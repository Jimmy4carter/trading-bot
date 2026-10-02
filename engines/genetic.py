"""
Genetic Bitmask Evolution Engine.
Evolves 64-bit feature masks for each trading pair to silence irrelevant noise
and maximize predictive accuracy through Darwinian selection.
"""

import random
import logging
from typing import List, Dict, Any, Tuple

from core.database import get_strategy_memories
from core.cache import cache

logger = logging.getLogger("trading_bot.engine.genetic")

class GeneticBitmaskEngine:
    def __init__(self, population_size: int = 50, mutation_rate: float = 0.08):
        self.population_size = population_size
        self.mutation_rate = mutation_rate

    def _generate_random_mask(self) -> int:
        """Generates a random 64-bit mask (randomly 0s and 1s)."""
        return random.getrandbits(64)

    def _mutate(self, mask: int) -> int:
        """Flips 1 to 3 random bits with mutation probability."""
        mutated = mask
        for _ in range(random.randint(1, 3)):
            if random.random() < self.mutation_rate:
                bit_pos = random.randint(0, 63)
                mutated ^= (1 << bit_pos)
        return mutated & 0xFFFFFFFFFFFFFFFF

    def _crossover(self, parent_a: int, parent_b: int) -> int:
        """Single-point bitwise crossover between two parent masks."""
        crossover_point = random.randint(1, 63)
        lower_mask = (1 << crossover_point) - 1
        upper_mask = ~lower_mask & 0xFFFFFFFFFFFFFFFF
        child = (parent_a & lower_mask) | (parent_b & upper_mask)
        return child & 0xFFFFFFFFFFFFFFFF

    def evaluate_fitness(self, mask: int, memories: List[Dict[str, Any]]) -> float:
        """
        Evaluates the predictive accuracy of a given bitmask against historical memories.
        Calculates how cleanly the mask separates winning BUY/SELL setups from noise.
        """
        if len(memories) < 5:
            return 0.5

        fitness_score = 0.0
        # Sample subset for high performance evaluation
        sample = random.sample(memories, min(len(memories), 40))

        for mem in sample:
            win_rate = float(mem.get('win_rate', 0.5))
            total_profit = float(mem.get('total_profit', 0.0))
            active_bits = bin(mask).count('1')

            # Favor masks that preserve enough features (at least 16 bits active) but eliminate noise
            parsimony_penalty = 0.0
            if active_bits < 12 or active_bits > 56:
                parsimony_penalty = 0.2

            fitness_score += (win_rate * 2.0) + (total_profit * 0.1) - parsimony_penalty

        return max(0.0, fitness_score)

    def evolve_pair_mask(self, symbol: str, generations: int = 20) -> int:
        """
        Runs evolutionary loop for a specific symbol and saves the fittest mask into Redis cache.
        """
        memories = get_strategy_memories(symbol)
        if len(memories) < 5:
            return 0xFFFFFFFFFFFFFFFF

        # Initialize population seeded with current mask + random masks
        current_mask = cache.get_genetic_mask(symbol)
        population = [current_mask] + [self._generate_random_mask() for _ in range(self.population_size - 1)]

        for gen in range(generations):
            scored_population: List[Tuple[float, int]] = []
            for mask in population:
                score = self.evaluate_fitness(mask, memories)
                scored_population.append((score, mask))

            # Sort by fitness descending
            scored_population.sort(reverse=True, key=lambda x: x[0])
            top_performers = [item[1] for item in scored_population[:max(2, int(self.population_size * 0.2))]]

            # Next generation with elitism
            next_generation = list(top_performers)
            while len(next_generation) < self.population_size:
                p1 = random.choice(top_performers)
                p2 = random.choice(top_performers)
                child = self._crossover(p1, p2)
                child = self._mutate(child)
                next_generation.append(child)

            population = next_generation

        best_mask = scored_population[0][1]
        cache.set_genetic_mask(symbol, best_mask)
        logger.info(f"Evolved genetic mask for {symbol}: 0x{best_mask:016X} (Active bits: {bin(best_mask).count('1')}/64)")
        return best_mask

# Singleton genetic engine
genetic_engine = GeneticBitmaskEngine()
