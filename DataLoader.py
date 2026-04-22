import json

def buildLoader():
    with open("Buildings_ERE.JSON") as b:
        data = json.load(b)
    return data["buildings"], 

def rsrcLoader():
    with open("Resources_ERE.JSON") as r:
        data = json.load(r)
    return data["resources"]
    
def regionLoader():
    with open("RegionDataset.JSON") as d:
        data = json.load(d)
    return data