from .sokoban import Sokoban

# Boxoban-style: 10x10 room, 4 boxes. Generated locally; DeepMind's level files can be added as a loader later.
def boxoban_level(rng):
    return Sokoban.random_level(rng, H=10, W=10, boxes=4, wall_prob=0.05)
