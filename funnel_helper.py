def elimination_check(game_dict, d, user_dict):

    games_left = 0
    total_games = 0 # can no longer rely on length of game dict with canceled games - thank you covid
    total_users = len(d)
    eliminated_list = []
    curr_most_wins = next(iter(d.items()))[1]['wins']
    curr_winners = []
    winner = []
    tb_log = []

    # calculcate games left.. anything not scheduled doesn't count (ie canceled)
    for k, game in game_dict.items():
        if game['status']['status'] == 'Scheduled':
            games_left += 1
            total_games += 1
        elif game['status']['status'] != 'Canceled':
            total_games += 1

    games_left += 7
    print(f"games left: {games_left}")
    print(f"curr_most_winner from helper!!!: {curr_most_wins}")
    print(f"total games: {total_games}")

    # compare most with user wins vs games left to calc elim
    # and also prepare a list of users with the most wins
    for user, picks in d.items():
        print(f"user {user}: wins: {picks['wins']}  behind: {curr_most_wins - picks['wins']}")
        if curr_most_wins - picks['wins'] > games_left:
            print(f"user {user} is eliminated")
            eliminated_list.append(user)
        elif picks['wins'] == curr_most_wins:
            curr_winners.append(user)

    print(f"total users: {total_users} total elim: {len(eliminated_list)}")
    if total_users - len(curr_winners) - len(eliminated_list) == 0 and len(eliminated_list) != 0:
        winner = curr_winners
    print(f"WINNER:  {winner}")

    if len(winner) > 1 and games_left == 0:  # check tiebreaks
        teams = next(iter(reversed(game_dict.items())))[1]['competitors'] 
        total_score = 0
        for score in teams:
            total_score += int(score[2])
        print(f"total score {total_score}")

        min_diff = 1000
        tb_winner = []
        for user in winner:
            if abs(d[user]['tb'] - total_score) == min_diff:
                tb_winner.append(user)
                tb_log.append(f"{user_dict[user]} TB of {d[user]['tb']} is {abs(d[user]['tb'] - total_score)} away from total score of {total_score}")
            elif abs(d[user]['tb'] - total_score) < min_diff:
                tb_winner = [user]
                tb_log.insert(0, f"{user_dict[user]['username']}'s tie break of {d[user]['tb']} is {abs(d[user]['tb'] - total_score)} away from total score of {total_score}")
            else:
                tb_log.append(f"{user_dict[user]} TB of {d[user]['tb']} is {abs(d[user]['tb'] - total_score)} away from total score of {total_score}")
        winner = tb_winner
        print(f"winner in helper {winner}")

    return {'elim': eliminated_list, 'winner': winner, 'tb_log': tb_log}
