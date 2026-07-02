from typing import Union

from Library.Database.Dataframe import np

class MemoryAPI:

    def __init__(self,
                 size: int,
                 input_shape: tuple,
                 action_shape: int,
                 seed: Union[int, None] = None):
        self.size = size
        self.counter = 0
        self._rng = np.random.default_rng(seed)
        self.state_memory: np.ndarray = np.zeros((self.size, *input_shape))
        self.action_memory: np.ndarray = np.zeros((self.size, action_shape))
        self.reward_memory: np.ndarray = np.zeros(self.size)
        self.next_state_memory: np.ndarray = np.zeros((self.size, *input_shape))
        self.terminal_memory: np.ndarray = np.zeros(self.size, dtype=np.bool_)

    def memorize(self, state, action, reward, next_state, done) -> None:
        index = self.counter % self.size
        self.state_memory[index] = state
        self.action_memory[index] = action
        self.reward_memory[index] = reward
        self.next_state_memory[index] = next_state
        self.terminal_memory[index] = done
        self.counter += 1

    def remember(self, batch_size) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray):
        max_mem = min(self.counter, self.size)
        batch = self._rng.choice(max_mem, batch_size)
        states = self.state_memory[batch]
        actions = self.action_memory[batch]
        rewards = self.reward_memory[batch]
        next_states = self.next_state_memory[batch]
        dones = self.terminal_memory[batch]
        return states, actions, rewards, next_states, dones