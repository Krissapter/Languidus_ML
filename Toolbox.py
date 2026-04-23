import json
from sklearn.model_selection import train_test_split

def buildLoader():
    with open("Buildings_ERE.JSON") as b:
        data = json.load(b)
    return data["buildings"]

def rsrcLoader():
    with open("Resources_ERE.JSON") as r:
        data = json.load(r)
    return data["resources"]
    
def regionLoader():
    with open("RegionDataset.JSON") as d:
        data = json.load(d)
    return data

def contextSplitter(contexts):
    temp, test = train_test_split(contexts, train_size=0.85, random_state=42)
    train, val = train_test_split(temp, train_size=0.90, random_state=42)
    return train, val, test

#This is not necessary but does improve readability from details, If efficiency is the game, drop this and do an array instead
def parseContext(contextArr):
    return{
        "fertility": contextArr[0],
        "coast": contextArr[1:4],
        "hasResource": contextArr[4:7],
        "resources": contextArr[7:10]
    }
