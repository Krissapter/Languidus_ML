import gymnasium as gym
import numpy as np

class LanguidusEnv(gym.Env):
    def __init__(self, buildings, regionContext):
        super().__init__()
        self.buildings = buildings #list of buildings
        self.regionContext = regionContext #Fertility, coastline & resources
        self.slots = [None] * 11 #The funny input vector array

        def reset(self):
            pass
        def step(self, action):
            pass