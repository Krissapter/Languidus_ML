import matplotlib.pyplot as plt
import numpy as np
import time
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from LanguidusEnvironment import LanguidusEnv
from LanguidusMockExam import mockExam
from Toolbox import buildLoader, regionLoader, contextSplitter
buildingList = buildLoader()
contexts = regionLoader()

trainCtx, valCtx, testCtx = contextSplitter(contexts)

env = LanguidusEnv(buildingList, trainCtx)
env = ActionMasker(env, lambda e: e.getActionMask())
env = DummyVecEnv([lambda: env])
env = VecNormalize(env, norm_obs=False, norm_reward=True, clip_reward=10.0)

model = MaskablePPO("MlpPolicy", env, verbose=0, ent_coef=0.05,
                    policy_kwargs=dict(net_arch=[256, 256, 128]))

class RewardCallback(BaseCallback):
    def __init__(self):
        super().__init__()
        self.episodeRewards = []
    
    def _on_step(self):
        if self.locals["dones"][0]:
            rawReward = self.locals["infos"][0]["raw_reward"]
            self.episodeRewards.append(rawReward[0])
        return True
    
def train(hours):
    callback = RewardCallback()
    valScores = []
    valAt = []
    startTime = time.time()
    limit = hours*3600
    trainingRound = 1
    levelUp1 = None
    levelUp2 = None
    passCombo = 0
    REQUIRED_COMBO = 3

    while(time.time() - startTime < limit):
        print(f"Round {trainingRound}")
        model.learn(100000, callback=callback, reset_num_timesteps=False)
        model.save("languidus_ppo")
        env.save("languidus_vecnormalize.pkl")

        if trainingRound % 1 == 0:
            scores = [mockExam(ctx, model, env.venv.envs[0].env.stage)[0] for ctx in valCtx[:500]]
            valMean = np.mean(scores)
            valScores.append(valMean)
            valAt.append(trainingRound)
            print(f"Validation mean: {valScores[-1]:.0f}")

            #TODO Make it check if it has run at least 10 rounds
            if env.env_method("getStage") == 0:
                if valMean > -500 and max(scores) >= 0:
                    passCombo += 1
                    print(f"{passCombo}/{REQUIRED_COMBO}")
                    if passCombo >= REQUIRED_COMBO:
                        env.env_method("setStage", 1)
                        levelUp1=trainingRound
                        passCombo = 0
                        print("Level Up! 0 --> 1")
                else:
                    passCombo = 0
                    
            elif env.env_method("getStage")==1 and valMean > 8000:
                passCombo += 1
                print(f"{passCombo}/{REQUIRED_COMBO}")
                if passCombo >= REQUIRED_COMBO:
                    env.env_method("setStage", 2)
                    levelUp2 = trainingRound
                    print("Level Up! 1 --> 2")
            else:
                passCombo = 0
                                      
        
        trainingRound += 1
    if levelUp2 is not None:
        plotRewards(callback.episodeRewards, valScores, valAt, levelUp1, levelUp2)
    elif levelUp1 is not None:
        plotRewards(callback.episodeRewards, valScores, valAt, levelUp1)
    else:
        plotRewards(callback.episodeRewards, valScores, valAt)
    
def plotRewards(rewards, valScores, valAt, levelOne=None, levelTwo=None, window=100):
    rewards = np.array(rewards).flatten()
    epPerRound= 100000//11
    valAtEpisodes = [r * epPerRound for r in valAt]

    rollingMean = np.convolve(rewards, np.ones(window)/window, mode="valid")
    rollingMin = [rewards[i:i+window].min() for i in range(len(rewards)-window+1)]
    rollingMax = [rewards[i:i+window].max() for i in range(len(rewards)-window+1)]
    x = range(len(rollingMean))

    plt.figure(figsize=(12,6))
    plt.plot(x, rollingMean, label="Training Mean")
    plt.plot(valAtEpisodes, valScores, "r-o", label="Validation Mean", linewidth=2)
    plt.fill_between(x, rollingMin, rollingMax, alpha=0.2, label= "Min/Max range")
    if levelOne is not None:
        levelOne = levelOne*epPerRound
        plt.axvline(levelOne, color="green", linewidth=1.5, linestyle="--")
        plt.text(levelOne, plt.ylim()[1] * 0.95, "Level 1", color="green", fontsize=9)
    if levelTwo is not None:
        levelTwo = levelTwo*epPerRound
        plt.axvline(levelTwo, color="magenta", linewidth=1.5, linestyle="--")
        plt.text(levelTwo, plt.ylim()[1] * 0.95, "Level 2", color="magenta", fontsize=9)
    plt.grid()
    plt.ylim((-5e3, 25e3))
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.title("Languidus PPO Training")
    plt.legend()
    plt.savefig("training_progress.png")
    plt.show()

train(0.1)