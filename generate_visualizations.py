"""Generate all 6 World Cup 2026 visualizations using ranking fallback scores."""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from itertools import combinations
from collections import defaultdict

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import accuracy_score

import warnings
warnings.filterwarnings('ignore')
np.random.seed(42)

DATA_DIR = Path('data')
VIZ_DIR  = Path('visualizations')
VIZ_DIR.mkdir(exist_ok=True)

C = {
    'accent': '#EF6545',
    'cool':   '#AECFD0',
    'warm':   '#F49625',
    'dark':   '#422F0E',
    'bg':     '#F5E6C0',
    'teal':   '#037F71',
    'muted':  '#7A5C50',
}
CONF_COLORS = {
    'UEFA': C['cool'], 'CONMEBOL': C['accent'], 'AFC': C['warm'],
    'CAF':  C['teal'], 'CONCACAF': C['dark'],  'OFC': C['muted'],
}

RANKING_SCORES = {
    'Argentina':57.0,'France':56.0,'England':55.0,'Brazil':54.5,
    'Portugal':54.0,'Spain':53.5,'Netherlands':53.0,'Belgium':52.0,
    'Germany':51.5,'Croatia':50.0,'Uruguay':49.5,'Colombia':49.0,
    'Morocco':48.0,'Switzerland':47.5,'Norway':48.5,'Japan':47.0,
    'Senegal':46.5,'Mexico':46.0,'United States':45.5,'South Korea':45.0,
    'Turkey':44.5,'Ecuador':44.0,'Australia':43.0,'Sweden':47.0,
    'Iran':42.5,'Canada':42.0,'Scotland':40.0,'Austria':40.0,
    'Ivory Coast':39.5,'Ghana':38.5,'Czech Republic':37.5,'Tunisia':36.5,
    'Egypt':36.0,'Saudi Arabia':35.5,'South Africa':35.0,'Algeria':35.0,
    'Paraguay':38.0,'Panama':33.5,'Qatar':34.0,'Bosnia and Herzegovina':33.0,
    'New Zealand':31.5,'Iraq':30.5,'Uzbekistan':30.0,'DR Congo':30.0,
    'Jordan':28.5,'Cape Verde':29.0,'Haiti':27.0,'Curacao':26.0,
}

TEAM_CONF = {
    'Argentina':'CONMEBOL','Brazil':'CONMEBOL','Colombia':'CONMEBOL',
    'Uruguay':'CONMEBOL','Ecuador':'CONMEBOL','Paraguay':'CONMEBOL',
    'United States':'CONCACAF','Mexico':'CONCACAF','Canada':'CONCACAF',
    'Panama':'CONCACAF','Haiti':'CONCACAF','Curacao':'CONCACAF',
    'France':'UEFA','England':'UEFA','Portugal':'UEFA','Spain':'UEFA',
    'Netherlands':'UEFA','Germany':'UEFA','Croatia':'UEFA',
    'Switzerland':'UEFA','Austria':'UEFA','Turkey':'UEFA',
    'Czech Republic':'UEFA','Belgium':'UEFA','Scotland':'UEFA',
    'Norway':'UEFA','Sweden':'UEFA','Bosnia and Herzegovina':'UEFA',
    'Japan':'AFC','South Korea':'AFC','Iran':'AFC','Australia':'AFC',
    'Saudi Arabia':'AFC','Iraq':'AFC','Jordan':'AFC','Uzbekistan':'AFC',
    'Qatar':'AFC',
    'Morocco':'CAF','Senegal':'CAF','Egypt':'CAF',
    'Ivory Coast':'CAF','Ghana':'CAF','South Africa':'CAF',
    'Tunisia':'CAF','Algeria':'CAF','Cape Verde':'CAF','DR Congo':'CAF',
    'New Zealand':'OFC',
}

GROUPS_2026 = {
    'Group A': ['Mexico','South Africa','South Korea','Czech Republic'],
    'Group B': ['Canada','Switzerland','Qatar','Bosnia and Herzegovina'],
    'Group C': ['Brazil','Morocco','Scotland','Haiti'],
    'Group D': ['United States','Paraguay','Australia','Turkey'],
    'Group E': ['Germany','Curacao','Ivory Coast','Ecuador'],
    'Group F': ['Netherlands','Japan','Tunisia','Sweden'],
    'Group G': ['Belgium','Egypt','Iran','New Zealand'],
    'Group H': ['Spain','Cape Verde','Saudi Arabia','Uruguay'],
    'Group I': ['France','Senegal','Norway','Iraq'],
    'Group J': ['Argentina','Algeria','Austria','Jordan'],
    'Group K': ['Portugal','Colombia','Uzbekistan','DR Congo'],
    'Group L': ['England','Croatia','Ghana','Panama'],
}

all_teams_2026 = [t for teams in GROUPS_2026.values() for t in teams]
team_scores = RANKING_SCORES.copy()

# ── Historical WC matches ──────────────────────────────────────────────────────
print("Loading historical WC matches...")
df_hist = pd.read_csv(DATA_DIR / 'historical_results.csv')
df_wc = df_hist[df_hist['tournament'] == 'FIFA World Cup'].copy()
df_wc['date'] = pd.to_datetime(df_wc['date'])
df_wc = df_wc.sort_values('date').reset_index(drop=True)
df_wc['result'] = df_wc.apply(
    lambda r: 0 if r['home_score'] > r['away_score']
              else (1 if r['home_score'] == r['away_score'] else 2), axis=1
)
print(f"  {len(df_wc)} WC matches, {df_wc['date'].dt.year.min()}–{df_wc['date'].dt.year.max()}")

# ── Elo ratings ────────────────────────────────────────────────────────────────
def expected_elo(ra, rb): return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
def update_elo(rating, expected, actual, k=40): return rating + k * (actual - expected)

def calculate_elo_ratings(df):
    elos = defaultdict(lambda: 1500.0)
    for _, row in df.iterrows():
        h, a = row['home_team'], row['away_team']
        exp_h = expected_elo(elos[h], elos[a])
        actual_h = 1.0 if row['result'] == 0 else (0.5 if row['result'] == 1 else 0.0)
        elos[h] = update_elo(elos[h], exp_h, actual_h)
        elos[a] = update_elo(elos[a], 1-exp_h, 1-actual_h)
    return dict(elos)

team_elos = calculate_elo_ratings(df_wc)
print(f"  Elo ratings computed for {len(team_elos)} teams")

# ── H2H stats ──────────────────────────────────────────────────────────────────
def h2h_stats(df, team1, team2, n=5):
    mask = (
        ((df['home_team'] == team1) & (df['away_team'] == team2)) |
        ((df['home_team'] == team2) & (df['away_team'] == team1))
    )
    recent = df[mask].tail(n)
    if len(recent) == 0:
        return 0.0, 0.0
    wins = sum(
        (r['home_team'] == team1 and r['result'] == 0) or
        (r['away_team'] == team1 and r['result'] == 2)
        for _, r in recent.iterrows()
    )
    draws = sum(r['result'] == 1 for _, r in recent.iterrows())
    return wins / n, draws / n

# ── Feature matrix ─────────────────────────────────────────────────────────────
print("Building feature matrix...")
elos_snapshot = defaultdict(lambda: 1500.0)
feature_rows = []
for _, row in df_wc.iterrows():
    h, a = row['home_team'], row['away_team']
    h_score = team_scores.get(h, np.mean(list(team_scores.values())))
    a_score = team_scores.get(a, np.mean(list(team_scores.values())))
    h_elo   = elos_snapshot[h]
    a_elo   = elos_snapshot[a]
    df_past = df_wc[df_wc['date'] < row['date']]
    h2w, h2d = h2h_stats(df_past, h, a)
    feature_rows.append({
        'strength_diff': round(h_score - a_score, 3),
        'elo_diff':      round(h_elo - a_elo, 1),
        'h2h_win_rate':  h2w,
        'h2h_draw_rate': h2d,
        'result':        row['result'],
    })
    exp_h = expected_elo(elos_snapshot[h], elos_snapshot[a])
    act_h = 1.0 if row['result'] == 0 else (0.5 if row['result'] == 1 else 0.0)
    elos_snapshot[h] = update_elo(elos_snapshot[h], exp_h, act_h)
    elos_snapshot[a] = update_elo(elos_snapshot[a], 1-exp_h, 1-act_h)

df_feat = pd.DataFrame(feature_rows)
FEATURE_COLS = ['strength_diff', 'elo_diff', 'h2h_win_rate', 'h2h_draw_rate']
print(f"  Feature matrix: {df_feat.shape}")

# ── Train models ───────────────────────────────────────────────────────────────
print("Training models...")
X = df_feat[FEATURE_COLS].values
y = df_feat['result'].values
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
scaler   = StandardScaler()
X_tr_sc  = scaler.fit_transform(X_train)
X_te_sc  = scaler.transform(X_test)
X_all_sc = scaler.transform(X)

lr = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=1000, C=1.0, random_state=42)
lr.fit(X_tr_sc, y_train)
lr_cv    = cross_val_score(lr, X_all_sc, y, cv=5, scoring='accuracy')
lr_train = accuracy_score(y_train, lr.predict(X_tr_sc))
lr_test  = accuracy_score(y_test,  lr.predict(X_te_sc))

rf = RandomForestClassifier(n_estimators=500, max_depth=10, min_samples_split=5, random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)
rf_cv    = cross_val_score(rf, X, y, cv=5, scoring='accuracy')
rf_train = accuracy_score(y_train, rf.predict(X_train))
rf_test  = accuracy_score(y_test,  rf.predict(X_test))

print(f"  LR CV: {lr_cv.mean():.3f} ± {lr_cv.std():.3f}")
print(f"  RF CV: {rf_cv.mean():.3f} ± {rf_cv.std():.3f}")

lr_coef_df = pd.DataFrame({
    'feature':  FEATURE_COLS,
    'home_win': lr.coef_[0].round(3),
    'draw':     lr.coef_[1].round(3),
    'away_win': lr.coef_[2].round(3),
})
rf_imp_df = pd.DataFrame({'feature': FEATURE_COLS, 'importance': rf.feature_importances_.round(4)}).sort_values('importance', ascending=False)

# ── Simulate tournament ────────────────────────────────────────────────────────
def build_features(t1, t2):
    s1 = team_scores.get(t1, np.mean(list(team_scores.values())))
    s2 = team_scores.get(t2, np.mean(list(team_scores.values())))
    e1 = team_elos.get(t1, 1500.0)
    e2 = team_elos.get(t2, 1500.0)
    h2w, h2d = h2h_stats(df_wc, t1, t2)
    return np.array([[s1 - s2, e1 - e2, h2w, h2d]])

def simulate_match(t1, t2, is_knockout=False):
    feats    = build_features(t1, t2)
    feats_sc = scaler.transform(feats)
    lr_probs = lr.predict_proba(feats_sc)[0]
    rf_probs = rf.predict_proba(feats)[0]
    results  = {}
    for name, probs in [('lr', lr_probs), ('rf', rf_probs)]:
        p_win, p_draw, p_lose = probs
        if is_knockout:
            total    = p_win + p_lose
            adj_win  = p_win  + p_draw * (p_win  / total if total > 0 else 0.5)
            adj_lose = p_lose + p_draw * (p_lose / total if total > 0 else 0.5)
            winner   = t1 if adj_win >= adj_lose else t2
            win_p    = max(adj_win, adj_lose)
        else:
            idx    = int(np.argmax(probs))
            winner = t1 if idx == 0 else (None if idx == 1 else t2)
            win_p  = probs[idx]
        results[name] = {'winner': winner, 'win_prob': round(win_p, 3),
                         'p_t1': round(p_win, 3), 'p_draw': round(p_draw, 3), 'p_t2': round(p_lose, 3)}
    return results

def simulate_group(teams):
    tables = {m: {t: {'pts': 0, 'gd': 0, 'gf': 0} for t in teams} for m in ('lr', 'rf')}
    for t1, t2 in combinations(teams, 2):
        res = simulate_match(t1, t2, is_knockout=False)
        for m in ('lr', 'rf'):
            w = res[m]['winner']
            if w == t1:
                tables[m][t1]['pts'] += 3; tables[m][t1]['gd'] += 1; tables[m][t1]['gf'] += 1; tables[m][t2]['gd'] -= 1
            elif w == t2:
                tables[m][t2]['pts'] += 3; tables[m][t2]['gd'] += 1; tables[m][t2]['gf'] += 1; tables[m][t1]['gd'] -= 1
            else:
                tables[m][t1]['pts'] += 1; tables[m][t2]['pts'] += 1
    return {m: sorted(tables[m].items(), key=lambda x: (x[1]['pts'],x[1]['gd'],x[1]['gf']), reverse=True) for m in ('lr','rf')}

print("Simulating group stage...")
group_standings = {g: simulate_group(teams) for g, teams in GROUPS_2026.items()}

def determine_advancement(group_standings, model='lr'):
    winners, runners, thirds = [], [], []
    for gname, stds in group_standings.items():
        s = stds[model]
        winners.append((s[0][0], gname, s[0][1]))
        runners.append((s[1][0], gname, s[1][1]))
        thirds.append((s[2][0], gname, s[2][1]))
    best_thirds = sorted(thirds, key=lambda x: (x[2]['pts'],x[2]['gd'],x[2]['gf']), reverse=True)[:8]
    return [t[0] for t in (winners + runners + best_thirds)]

adv_lr = determine_advancement(group_standings, 'lr')
adv_rf = determine_advancement(group_standings, 'rf')

def simulate_knockout_round(teams, model='lr', round_name=''):
    winners, matches = [], []
    for i in range(0, len(teams), 2):
        t1, t2 = teams[i], teams[i+1]
        res = simulate_match(t1, t2, is_knockout=True)
        w   = res[model]['winner']
        winners.append(w)
        matches.append({'round': round_name, 't1': t1, 't2': t2, 'winner': w,
                        'p_t1': res[model]['p_t1'], 'p_draw': res[model]['p_draw'], 'p_t2': res[model]['p_t2']})
    return winners, matches

def simulate_tournament(advancing, model='lr'):
    bracket, all_matches = {}, []
    current = list(advancing)
    np.random.shuffle(current)
    for rnd in ['Round of 32','Round of 16','Quarter-finals','Semi-finals','Final']:
        if len(current) < 2: break
        winners, matches = simulate_knockout_round(current, model, rnd)
        bracket[rnd] = {'matches': matches, 'winners': winners}
        all_matches.extend(matches)
        current = winners
    return current[0] if current else 'Unknown', bracket, pd.DataFrame(all_matches)

print("Simulating knockout stage...")
champion_lr, bracket_lr, matches_lr = simulate_tournament(adv_lr, 'lr')
champion_rf, bracket_rf, matches_rf = simulate_tournament(adv_rf, 'rf')
print(f"  LR champion: {champion_lr}")
print(f"  RF champion: {champion_rf}")

agree_count, total_count = 0, 0
for rnd in bracket_lr:
    for ml, mr in zip(bracket_lr[rnd]['matches'], bracket_rf.get(rnd, {}).get('matches', [])):
        total_count += 1
        if ml['winner'] == mr['winner']: agree_count += 1
print(f"  Agreement: {agree_count}/{total_count}")

# ═══════════════════════════════════════════════════════════════════════════════
# VIZ 1: Team Strength Rankings
# ═══════════════════════════════════════════════════════════════════════════════
print("\nGenerating team_strength.png...")
df_team_scores = pd.DataFrame([
    {'team': t, 'score': s, 'conf': TEAM_CONF.get(t,'OTHER')}
    for t, s in RANKING_SCORES.items()
]).sort_values('score', ascending=True)

fig, ax = plt.subplots(figsize=(14, 10))
fig.patch.set_facecolor(C['bg']); ax.set_facecolor(C['bg'])
colors = [CONF_COLORS.get(c, C['muted']) for c in df_team_scores['conf']]
ax.barh(df_team_scores['team'], df_team_scores['score'], color=colors, alpha=0.88, edgecolor='white', linewidth=0.4)
ax.set_xlabel('Composite Score (FIFA ranking-based)', fontsize=11, color=C['dark'])
ax.set_title('2026 World Cup — Team Strength Rankings', fontsize=15, fontweight='bold', color=C['dark'], pad=14)
ax.tick_params(axis='both', labelsize=8.5, colors=C['dark'])
ax.spines[['top','right','left']].set_visible(False)
legend_handles = [mpatches.Patch(color=v, label=k) for k, v in CONF_COLORS.items()]
ax.legend(handles=legend_handles, title='Confederation', fontsize=8, title_fontsize=9,
          loc='lower right', framealpha=0.7, facecolor=C['bg'])
plt.tight_layout()
out = VIZ_DIR / 'team_strength.png'
plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=C['bg'])
plt.close()
print(f"  Saved {out}")

# ═══════════════════════════════════════════════════════════════════════════════
# VIZ 2: Model Accuracy
# ═══════════════════════════════════════════════════════════════════════════════
print("Generating model_accuracy.png...")
fig, ax = plt.subplots(figsize=(7, 5))
fig.patch.set_facecolor(C['bg']); ax.set_facecolor(C['bg'])
models  = ['Logistic\nRegression', 'Random\nForest']
means   = [lr_cv.mean(), rf_cv.mean()]
stds    = [lr_cv.std(),  rf_cv.std()]
colors2 = [C['accent'], C['teal']]
bars = ax.bar(models, means, yerr=stds, color=colors2, alpha=0.85, capsize=7, edgecolor='white', linewidth=0.8, width=0.45)
ax.axhline(1/3, color=C['dark'], linestyle='--', linewidth=1.2, alpha=0.6, label='Random baseline (33.3%)')
for bar, mean, std in zip(bars, means, stds):
    ax.text(bar.get_x() + bar.get_width()/2, mean + std + 0.004,
            f'{mean:.1%}', ha='center', va='bottom', fontsize=11, fontweight='bold', color=C['dark'])
ax.set_ylabel('Cross-validation Accuracy (5-fold)', fontsize=10, color=C['dark'])
ax.set_title('Model Performance Comparison', fontsize=13, fontweight='bold', color=C['dark'], pad=10)
ax.set_ylim(0, max(means) + max(stds) + 0.08)
ax.legend(fontsize=9, framealpha=0.7, facecolor=C['bg'])
ax.tick_params(colors=C['dark'])
ax.spines[['top','right']].set_visible(False)
plt.tight_layout()
out = VIZ_DIR / 'model_accuracy.png'
plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=C['bg'])
plt.close()
print(f"  Saved {out}")

# ═══════════════════════════════════════════════════════════════════════════════
# VIZ 3: Feature Importance
# ═══════════════════════════════════════════════════════════════════════════════
print("Generating feature_importance.png...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
fig.patch.set_facecolor(C['bg'])
for ax in (ax1, ax2): ax.set_facecolor(C['bg'])

lr_coefs = lr_coef_df.sort_values('home_win', ascending=True)
bar_colors = [C['accent'] if v >= 0 else C['cool'] for v in lr_coefs['home_win']]
ax1.barh(lr_coefs['feature'], lr_coefs['home_win'], color=bar_colors, alpha=0.85, edgecolor='white')
ax1.axvline(0, color=C['dark'], linewidth=0.8)
ax1.set_title('Logistic Regression\nCoefficients (home-win class)', fontsize=10, fontweight='bold', color=C['dark'])
ax1.tick_params(axis='both', labelsize=9, colors=C['dark'])
ax1.spines[['top','right']].set_visible(False)

rf_imp = rf_imp_df.sort_values('importance', ascending=True)
ax2.barh(rf_imp['feature'], rf_imp['importance'], color=C['teal'], alpha=0.85, edgecolor='white')
ax2.set_title('Random Forest\nFeature Importances', fontsize=10, fontweight='bold', color=C['dark'])
ax2.tick_params(axis='both', labelsize=9, colors=C['dark'])
ax2.spines[['top','right']].set_visible(False)

fig.suptitle('What Drives Match Outcomes?', fontsize=13, fontweight='bold', color=C['dark'], y=1.02)
plt.tight_layout()
out = VIZ_DIR / 'feature_importance.png'
plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=C['bg'])
plt.close()
print(f"  Saved {out}")

# ═══════════════════════════════════════════════════════════════════════════════
# VIZ 4: Bracket Comparison
# ═══════════════════════════════════════════════════════════════════════════════
print("Generating bracket_comparison.png...")
AGREE_COLOR    = '#B8E0C0'
DISAGREE_COLOR = '#F5C6B8'
round_order = ['Round of 32','Round of 16','Quarter-finals','Semi-finals','Final']

fig, axes = plt.subplots(1, 5, figsize=(18, 5))
fig.patch.set_facecolor(C['bg'])
fig.suptitle('Predicted Bracket: Where Models Agree vs Disagree', fontsize=13, fontweight='bold', color=C['dark'], y=1.02)

for col_idx, rnd in enumerate(round_order):
    ax = axes[col_idx]
    ax.set_facecolor(C['bg'])
    ax.set_title(rnd, fontsize=8.5, fontweight='bold', color=C['dark'])
    ax.axis('off')
    matches_l = bracket_lr.get(rnd, {}).get('matches', [])
    matches_r = bracket_rf.get(rnd, {}).get('matches', [])
    n = len(matches_l)
    if n == 0: continue
    for row_idx, (ml, mr) in enumerate(zip(matches_l, matches_r)):
        agree = ml['winner'] == mr['winner']
        bg    = AGREE_COLOR if agree else DISAGREE_COLOR
        y_pos = 1.0 - (row_idx / max(n, 1))
        rect = mpatches.FancyBboxPatch(
            (0.0, y_pos - 0.08), 1.0, 0.14,
            boxstyle="round,pad=0.01", linewidth=0.6,
            edgecolor=C['muted'], facecolor=bg, transform=ax.transAxes, clip_on=False
        )
        ax.add_patch(rect)
        ax.text(0.5, y_pos + 0.02, f"{ml['t1']} vs\n{ml['t2']}", ha='center', va='bottom',
                fontsize=5.5, color=C['dark'], transform=ax.transAxes, fontweight='bold')
        ax.text(0.5, y_pos - 0.03, f"LR: {ml['winner']}", ha='center', va='top',
                fontsize=4.5, color='#1A5C2A' if agree else '#8B2500', transform=ax.transAxes)
        ax.text(0.5, y_pos - 0.07, f"RF: {mr['winner']}", ha='center', va='top',
                fontsize=4.5, color='#1A5C2A' if agree else '#8B2500', transform=ax.transAxes)

legend_h = [mpatches.Patch(color=AGREE_COLOR, label='Models agree'), mpatches.Patch(color=DISAGREE_COLOR, label='Models disagree')]
fig.legend(handles=legend_h, loc='lower center', ncol=2, fontsize=9, bbox_to_anchor=(0.5, -0.04), framealpha=0.8, facecolor=C['bg'])
plt.tight_layout()
out = VIZ_DIR / 'bracket_comparison.png'
plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=C['bg'])
plt.close()
print(f"  Saved {out}")

# ═══════════════════════════════════════════════════════════════════════════════
# VIZ 5 & 6: Choropleth maps (matplotlib-based fallback since kaleido may not be installed)
# ═══════════════════════════════════════════════════════════════════════════════
ROUND_SCORE = {'Group exit':1,'Round of 32':2,'Round of 16':3,'Quarter-finals':4,'Semi-finals':5,'Final':6,'Winner':7}

def build_progression(bracket, all_teams, champion):
    prog = {t: 1 for t in all_teams}
    for rnd, info in bracket.items():
        for m in info['matches']:
            for t in (m['t1'], m['t2']):
                prog[t] = max(prog.get(t, 1), ROUND_SCORE.get(rnd, 2) - 1)
            prog[m['winner']] = max(prog.get(m['winner'], 1), ROUND_SCORE.get(rnd, 2))
    if champion: prog[champion] = ROUND_SCORE['Winner']
    return prog

prog_lr = build_progression(bracket_lr, all_teams_2026, champion_lr)
prog_rf = build_progression(bracket_rf, all_teams_2026, champion_rf)

STAGE_LABELS = {1:'Group exit',2:'Round of 32',3:'Round of 16',4:'Quarter-finals',5:'Semi-finals',6:'Final',7:'Winner'}

def make_choropleth_bar(prog, champion, model_name, filename):
    """Create a horizontal bar chart as choropleth substitute."""
    df = pd.DataFrame([
        {'team': t, 'depth': d, 'stage': STAGE_LABELS.get(d,'?'),
         'conf': TEAM_CONF.get(t,'OTHER')}
        for t, d in prog.items()
    ]).sort_values('depth', ascending=True)

    fig, ax = plt.subplots(figsize=(14, 11))
    fig.patch.set_facecolor(C['bg']); ax.set_facecolor(C['bg'])

    cmap_colors = ['#F5E6C0','#F4C97A','#F49625','#EF6545','#C0392B','#7D1A0A','#422F0E']
    bar_colors = [cmap_colors[min(d-1,6)] for d in df['depth']]

    bars = ax.barh(df['team'], df['depth'], color=bar_colors, alpha=0.90, edgecolor='white', linewidth=0.5)

    for bar, (_, row) in zip(bars, df.iterrows()):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                row['stage'], va='center', fontsize=7, color=C['dark'])

    ax.set_xlabel('Tournament Round', fontsize=11, color=C['dark'])
    ax.set_title(f'2026 WC Predicted Progression — {model_name} (🏆 {champion})',
                 fontsize=13, fontweight='bold', color=C['dark'], pad=12)
    ax.set_xlim(0, 8.5)
    ax.set_xticks(range(1, 8))
    ax.set_xticklabels(['Group\nexit','R32','R16','QF','SF','Final','Winner'], fontsize=8, color=C['dark'])
    ax.tick_params(axis='y', labelsize=8, colors=C['dark'])
    ax.spines[['top','right']].set_visible(False)

    plt.tight_layout()
    out = VIZ_DIR / filename
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=C['bg'])
    plt.close()
    print(f"  Saved {out}")

print("Generating choropleth_lr.png...")
make_choropleth_bar(prog_lr, champion_lr, 'Logistic Regression', 'choropleth_lr.png')
print("Generating choropleth_rf.png...")
make_choropleth_bar(prog_rf, champion_rf, 'Random Forest', 'choropleth_rf.png')

print("\nAll 6 visualizations generated!")
for f in sorted(VIZ_DIR.iterdir()):
    size = f.stat().st_size // 1024
    print(f"  {f.name}: {size}KB")
