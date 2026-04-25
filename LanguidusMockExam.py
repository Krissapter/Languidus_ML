import numpy as np
import matplotlib.pyplot as plt
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

def mockExam(context, model, stage = 2):
    innerEnv = LanguidusEnv(buildingList, [context])
    innerEnv.regionContext = context
    innerEnv.slots = [0]*11
    innerEnv.currentStats = None
    obs = innerEnv.getObs()

    for _ in range(11):
        mask = innerEnv.getActionMask()
        action, _ = model.predict(obs,action_masks=mask, deterministic=True)
        obs, _, done, _, _ = innerEnv.step(action)
        if done == True:
            break
    
    regArray = innerEnv.buildRegion()
    score, details = evaluate(regArray, buildingList, rsrcList, stage)

    return score, details, innerEnv.slots

def printGrade(slots, details, context, i, score):
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
            getBuilding(buildingList, rsrcList, slots[j], resources[sIdx], coast[sIdx])["name"]
            for j in range(start, end)
        ]
        print(f"    {sType.capitalize()}: {', '.join(names)}")
    print(f"\n  Stats:")
    print(f"    Food:      {r['food']}")
    print(f"    Happiness: {r['happiness']}")
    print(f"    Sanitation (city/town1/town2): {san}")
    print(f"    Wealth:    {r['wealth']}")
    print(f"    Trade:     {r['trade_value']}")
    print(f"\n  Final Score: {score}")



def plotGrades(scores):
    mean = np.mean(scores)
    std = np.std(scores)

    plt.figure(figsize=(12, 6))
    plt.hist(scores, bins=50, alpha=0.7, color="steelblue", edgecolor="black")
    plt.axvline(mean, color="red", linewidth=2, label=f"Mean: {mean:.0f}")
    plt.axvline(mean+std, color="orange", linewidth=1.5, linestyle="--", label=f"+1 STD: {mean+std:.0f}")
    plt.axvline(mean-std, color="orange", linewidth=1.5, linestyle="--", label=f"-1 STD: {mean-std:.0f}")
    plt.xlabel("Score")
    plt.ylabel("Frequency")
    plt.title("Languidus Mock Exam Score Distribution")
    plt.legend()
    plt.grid()
    plt.savefig("Mock_Exam_Results.png")
    plt.show()

    print(f"\nMean:  {mean:.0f}")
    print(f"STD:   {std:.0f}")
    print(f"Min:   {min(scores)}")
    print(f"Max:   {max(scores)}")

if __name__ == "__main__":
    env = LanguidusEnv(buildingList, valCtx)
    env = ActionMasker(env, lambda e: e.getActionMask())
    env = DummyVecEnv([lambda: env])
    env = VecNormalize.load("languidus_vecnormalize.pkl", env)
    env.training = False
    env.norm_reward = False

    modelDef = MaskablePPO.load("languidus_ppo", env=env)
    
    scores = []
    for i, ctx in enumerate(valCtx):
        score, details, slots = mockExam(ctx, modelDef)
        printGrade(slots, details, ctx, i, score)
        scores.append(score)
    plotGrades(scores)