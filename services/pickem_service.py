from db_accessor.db_accessor import db2


def get_pickem_games(season, detailed=False):
    g = "SELECT DISTINCT g.gameid, g.game_name, g.fav, g.spread, g.dog, g.locked FROM pickem.games g INNER JOIN (SELECT gameid, MAX(id) as maxid FROM pickem.games GROUP BY gameid) gg ON g.gameid = gg.gameid AND g.id = gg.maxid WHERE season = %s ORDER BY g.gameid ASC"
    games = db2(g, (season,))

    class Game:
        def __init__(self, game_name, fav, spread, dog, locked, winner="TBD"):
            self.game_name = game_name
            self.fav = fav
            self.spread = spread
            self.dog = dog
            self.locked = locked
            self.winner = winner

    s = "SELECT gameid, fav_score, dog_score FROM pickem.pickem_scores ORDER BY score_id DESC;"
    scores = db2(s)
    score_dict = {}
    for score in scores:
        if score[0] not in score_dict:
            score_dict[score[0]] = {'fav': score[1], 'dog': score[2]}

    game_list = [x for x in range(1, 14)]
    game_dict = {}
    for g in games:
        game_dict[g[0]] = Game(g[1], g[2], g[3], g[4], g[5])
        if g[0] in score_dict:
            if (score_dict[g[0]]['fav'] + game_dict[g[0]].spread) - score_dict[g[0]]['dog'] > 0:
                game_dict[g[0]].winner = game_dict[g[0]].fav.upper()
            else:
                game_dict[g[0]].winner = game_dict[g[0]].dog.upper()

    for n in range(len(game_dict) + 1, 14):
        game_dict[n] = Game('TBD', 'TBD', 0, 'TBD', False)

    if detailed == False:
        return game_list
    else:
        return game_dict


def sref_to_pickem(convention='p'):
    p = {
        "nor": "NO",  "min": "MIN",
        "det": "DET", "tam": "TPA",
        "crd": "ARI", "sfo": "SF",
        "rai": "LV",  "mia": "MIA",
        "rav": "BAL", "nyg": "NYG",
        "pit": "PIT", "clt": "IND",
        "nyj": "NYJ", "cle": "CLE",
        "kan": "KC",  "atl": "ATL",
        "jax": "JAX", "chi": "CHI",
        "htx": "HOU", "cin": "CIN",
        "was": "WAS", "car": "CAR",
        "sdg": "LAC", "den": "DEN",
        "sea": "SEA", "ram": "LAR",
        "dal": "DAL", "phi": "PHI",
        "gnb": "GB",  "oti": "TEN",
        "nwe": "NE",  "buf": "BUF",
    }

    if convention == 's':
        return dict([(value, key) for key, value in p.items()])
    else:
        return p
