from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from LanguidusEnvironment import LanguidusEnv
from LanguidusEvaluation import evaluate, getBuilding
from Toolbox import buildLoader, rsrcLoader, regionLoader, contextSplitter, parseContext



buildingList = buildLoader()
rsrcList = rsrcLoader()
context = regionLoader()

_, valCtx, _ = contextSplitter(context)

env = LanguidusEnv(buildingList, valCtx)
env = ActionMasker(env, lambda e: e.getActionMask())
env = DummyVecEnv([lambda: env])
env = VecNormalize.load("languidus_vecnormalize.pkl", env)
env.training = False
env.norm_reward = False

model = MaskablePPO.load("languidus_ppo", env=env)

def mockExam(context):
    innerEnv = LanguidusEnv(buildingList, [context])
    innerEnv.regionContext = context
    innerEnv.slots = [0]*11
    innerEnv.currentStats = None
    obs = innerEnv.getObs()

    for _ in range(11):
        mask = innerEnv.getActionMask()
        action, _ = model.predict(obs,action_masks=mask, deterministic=True)
        slotIdx = action // 27
        buildingId = action % 27
        innerEnv.slots[slotIdx] = int(buildingId)
        obs=innerEnv.getObs()
    
    regArray = innerEnv.buildRegion()
    score, details = evaluate(regArray, buildingList, rsrcList)

    return score, details, innerEnv.slots

def printGrade(slots, details, context, i):
    ctx = parseContext(context)
    resources = ctx["resources"]
    coast = ctx["coast"]
    r = details["region"]
    san = details["settlement_sanitation"]

    slotGroups = [(0,5, "city"), (5, 8, "town"), (8, 11, "town")]

    print(f"\n{'='*50}")
    print(f"TEST REGION {i+1}")
    print(f"  Fertility: {ctx['fertility']}  Coast: {coast}  Resources: {resources}")
    print(f"\n  Buildings:")
    for sIdx, (start, end, sType) in enumerate(slotGroups):
        names = [
            getBuilding(buildingList, rsrcList, slots[i], resources[sIdx], coast[sIdx])["name"]
            for i in range(start, end)
        ]
        print(f"    {sType.capitalize()}: {', '.join(names)}")
    print(f"\n  Stats:")
    print(f"    Food:      {r['food']}")
    print(f"    Happiness: {r['happiness']}")
    print(f"    Sanitation (city/town1/town2): {san}")
    print(f"    Wealth:    {r['wealth']}")
    print(f"    Trade:     {r['trade_value']}")
    print(f"\n  Final Score: {score}")

for i, ctx in enumerate(valCtx[:50]):
    score, details, slots = mockExam(ctx)
    printGrade(slots, details, ctx, i)