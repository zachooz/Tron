import os
import tensorflow as tf
from models import DeepQModel, DQPolicyGradientModel
import time
from customgame import CustomGame
import numpy as np

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'


def trainDQPG():
    """
    Trains DeepQModels
    """
    with tf.Session() as sess:
        gamma = 0.95

        model = DQPolicyGradientModel()

        sess.run(tf.global_variables_initializer())

        saver = tf.train.Saver()
        # players = [p1, p2]
        game = CustomGame()

        delay = 0.2

        exploration = 1
        sub = 0.01

        for i in range(1, 20000):
            visualize = i % 10 == 0
            # visualize = True
            if exploration < 0:
                exploration = 1
            else:
                exploration -= sub

            game.reset()
            print("Game", i, "exploration", exploration)
            hist = [{"states": [], "actions": [], "rewards": []}, {"states": [], "actions": [], "rewards": []}]
            while not (game.game_over()):
                ptm = game.player_to_move()

                i_board_state = game.get_game_parsed_state(ptm)
                actionDistribution = sess.run(model.output, feed_dict={model.input: i_board_state})
                action = np.random.choice(4, 1, p=actionDistribution[0])[0]
                if np.random.rand(1) < exploration:
                    if visualize:
                        print("random_move")
                    action = game.get_random_safe_move(ptm)
                game.take_num_action(action, ptm)
                rwd = game.score_state(ptm)
                hist[ptm]["states"].append(i_board_state)
                hist[ptm]["actions"].append(action)
                hist[ptm]["rewards"].append(rwd)

                if visualize:
                    print("E", exploration, "PTM", ptm, "action", action, game.num_to_action[action], "aDist", actionDistribution, "rwd", rwd)
                    game.visualize()
                    time.sleep(delay)

                if game.game_over():
                    # game is over so change op final value
                    op = ptm == 0
                    if(len(hist[op]["rewards"]) > 0):
                        hist[op]["rewards"][-1] = game.score_state(op)

                    # propagate gamma through time
                    pmtOffsetRewards = offsetRewardsByTime(hist[ptm]["rewards"][:], gamma)
                    opOffsetRewards = offsetRewardsByTime(hist[op]["rewards"][:], gamma)

                    ptm_input = np.squeeze(hist[ptm]["states"], axis=1)
                    op_input = np.squeeze(hist[op]["states"], axis=1)

                    if ptm_input.ndim == 1:
                        ptm_input = ptm_input.reshape(1, ptm_input.shape[0])

                    if op_input.ndim == 1:
                        op_input = op_input.reshape(1, op_input.shape[0])

                    if ptm_input.shape[1] > 0:
                        sess.run(model.optimizer,
                                 feed_dict={
                                    model.input: ptm_input,
                                    model.actions: hist[ptm]["actions"],
                                    model.rewards: pmtOffsetRewards})

                    if op_input.shape[1] > 0:
                        sess.run(model.optimizer,
                                 feed_dict={
                                    model.input: op_input,
                                    model.actions: hist[op]["actions"],
                                    model.rewards: opOffsetRewards})

                    if visualize:
                        print("Gameover: player", ptm, "rwd", game.score_state(ptm), "player", op, "rwd", game.score_state(op))

        save_path = saver.save(sess, "./model_data/dqpgm.ckpt")
        print("Model saved in path: %s" % save_path)


def offsetRewardsByTime(rewards, gamma):
    for i, e in reversed(list(enumerate(rewards))):
        if i + 1 == len(rewards):
            continue
        rewards[i] = rewards[i] + gamma * rewards[i + 1]
    return rewards


def trainDQ():
    """
    Trains DeepQModels
    """
    with tf.Session() as sess:
        gamma = 0.9
        # p1, p2 = DeepQModel(), DeepQModel()
        p1 = DeepQModel()
        # with tf.variable_scope("p1"):
        #     p1 = DeepQModel()
        # with tf.variable_scope("p2"):
        #     p2 = DeepQModel()

        sess.run(tf.global_variables_initializer())

        saver = tf.train.Saver()
        # players = [p1, p2]
        game = CustomGame()

        delay = 0.2

        exploration = 1
        num_e_steps = 100
        sub = exploration / num_e_steps

        for i in range(1, 100000):
            reset_distribution = i % num_e_steps == 0
            exploration -= sub
            visualize = i % 10 == 0
            # visualize = True

            game.reset()
            print("Game", i, "exploration", exploration)

            while not (game.game_over()):
                ptm = game.player_to_move()
                # model = players[ptm]
                model = p1
                i_board_state = game.get_game_parsed_state(ptm)
                nextQ = sess.run(model.qVal, feed_dict={model.input: i_board_state})
                action = np.argmax(nextQ)
                if np.random.rand(1) < exploration:
                    if visualize:
                        print("random_move")
                    action = game.get_random_safe_move(ptm)
                if visualize:
                    print("PTM", ptm, "action", action, game.num_to_action[action], "Q", nextQ)
                game.take_num_action(action, ptm)
                rwd = game.score_state(ptm)
                if game.game_over():
                    nextQ[0, action] = rwd
                    if visualize:
                        print("PTM", ptm, "PLAYER LOSS TRAINED ONs", nextQ, "reward", rwd)
                else:
                    opp = game.player_to_move()
                    board_state = game.get_game_parsed_state(opp)
                    oppAction = game.get_random_safe_move(opp)
                    game.see_num_action_result(oppAction, opp)
                    if game.state_over():
                        rwd = game.score_state(ptm)
                        board_state = game.get_game_parsed_state(ptm)
                        nQVal = sess.run(model.qVal, feed_dict={model.input: board_state})
                        nextQ[0, action] = rwd
                        if visualize:
                            print("Win action", game.num_to_action[action], action, game.num_to_action[action], "reward", rwd)
                    else:
                        board_state = game.get_game_parsed_state(ptm)
                        nQVal = sess.run(model.qVal, feed_dict={model.input: board_state})
                        nextQ[0, action] = rwd + gamma * np.amax(nQVal)
                        if visualize:
                            print("Neutral trained on", nextQ, "Estimate MAX", np.amax(nQVal), "nQEstimate", nQVal, "reward", rwd)

                game.rewind()
                if visualize:
                    print("TRAINED ON", nextQ)
                    game.visualize()
                    time.sleep(delay)

                sess.run(model.optimizer, feed_dict={model.input: i_board_state, model.nextQ: nextQ})

            if reset_distribution:
                exploration = 1
            if visualize:
                if game.game_over():
                    winner = game.get_results().index(1) + 1
                    print("Player %s won!" % winner)
                    print("Win Reward", game.score_state(game.get_results().index(1)))
                    print("Lose Reward", game.score_state(game.get_results().index(0)))

        save_path = saver.save(sess, "./model_data/dqm.ckpt")
        print("Model saved in path: %s" % save_path)


def main():
    trainDQPG()


if __name__ == "__main__":
    main()
