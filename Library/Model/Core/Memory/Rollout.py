from Library.Database.Dataframe import np
from Library.Utility.Typing import MISSING

class RolloutAPI:

    def __init__(self, input_shape: tuple, action_shape: int) -> None:
        self.input_shape = input_shape
        self.action_shape = action_shape
        self.counter = 0
        self.state_memory: list = []
        self.action_memory: list = []
        self.reward_memory: list = []
        self.next_state_memory: list = []
        self.terminal_memory: list = []

    def forget(self) -> None:
        self.state_memory.clear()
        self.action_memory.clear()
        self.reward_memory.clear()
        self.next_state_memory.clear()
        self.terminal_memory.clear()

    def memorize(self, state, action, reward, next_state, done) -> None:
        self.state_memory.append(state)
        self.action_memory.append(action)
        self.reward_memory.append(reward)
        self.next_state_memory.append(next_state)
        self.terminal_memory.append(done)
        self.counter += 1

    def remember(self, size: int = MISSING) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray):
        start = 0 if size is MISSING else max(0, len(self.reward_memory) - size)
        states = np.asarray(self.state_memory[start:], dtype=np.float64).reshape(-1, *self.input_shape)
        actions = np.asarray(self.action_memory[start:], dtype=np.float64).reshape(-1, self.action_shape)
        rewards = np.asarray(self.reward_memory[start:], dtype=np.float64)
        next_states = np.asarray(self.next_state_memory[start:], dtype=np.float64).reshape(-1, *self.input_shape)
        dones = np.asarray(self.terminal_memory[start:], dtype=np.bool_)
        return states, actions, rewards, next_states, dones