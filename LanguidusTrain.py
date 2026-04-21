from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from LanguidusEnvironment import LanguidusEnv
from LanguidusEvaluation import buildingList

regionContext = {
    "fertility": 3,
    "coast": [1, 0, 0],
    "hasResource": [0, 1, 0],
    "resources": [0, 1, 0]
}

env = LanguidusEnv(buildingList, regionContext)

env = ActionMasker(env, lambda e: e.getActionMask())

model = MaskablePPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=10000)

model.save("languidus_ppo")