# Copyright (c) 2008 Mikael Lind
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Python A* implementation: https://github.com/elemel/python-astar
"""

from heapq import heappush, heappop
from sys import maxint

F, H, NUM, G, POS, OPEN, VALID, PARENT = xrange(8)

def astar(start_pos, neighbors, goal, start_g, cost, heuristic, limit=maxint):
    # Create the start node.
    nums = iter(xrange(maxint))
    start_h = heuristic(start_pos)
    start = [start_g + start_h, start_h, nums.next(), start_g, start_pos, True,
             True, None]

    # Track all nodes seen so far.
    nodes = {start_pos: start}

    # Maintain a heap of nodes.
    heap = [start]

    # Track the best path found so far.
    best = start

    while heap:

        # Pop the next node from the heap.
        current = heappop(heap)
        current[OPEN] = False

        # Have we reached the goal?
        if goal(current[POS]):
            best = current
            break

        # Visit the neighbors of the current node.
        for neighbor_pos in neighbors(current[POS]):
            neighbor_g = current[G] + cost(current[POS], neighbor_pos)
            neighbor = nodes.get(neighbor_pos)
            if neighbor is None:

                # Limit the search.
                if len(nodes) >= limit:
                    import pyspades.block
                    raw_input('reached limit while trying path: %s -> %s' % (
                        start_pos, pyspades.block.goal_pos))
                    continue

                # We have found a new node.
                neighbor_h = heuristic(neighbor_pos)
                neighbor = [neighbor_g + neighbor_h, neighbor_h, nums.next(),
                            neighbor_g, neighbor_pos, True, True, current[POS]]
                nodes[neighbor_pos] = neighbor
                heappush(heap, neighbor)
                if neighbor_h < best[H]:

                    # We are approaching the goal.
                    best = neighbor

            elif neighbor_g < neighbor[G]:

                # We have found a better path to the neighbor.
                if neighbor[OPEN]:

                    # The neighbor is already open. Finding and updating it
                    # in the heap would be a linear complexity operation.
                    # Instead we mark the neighbor as invalid and make an
                    # updated copy of it.

                    neighbor[VALID] = False
                    nodes[neighbor_pos] = neighbor = neighbor[:]
                    neighbor[F] = neighbor_g + neighbor[H]
                    neighbor[NUM] = nums.next()
                    neighbor[G] = neighbor_g
                    neighbor[VALID] = True
                    neighbor[PARENT] = current[POS]
                    heappush(heap, neighbor)

                else:

                    # Reopen the neighbor.
                    neighbor[F] = neighbor_g + neighbor[H]
                    neighbor[G] = neighbor_g
                    neighbor[PARENT] = current[POS]
                    neighbor[OPEN] = True
                    heappush(heap, neighbor)

        # Discard leading invalid nodes from the heap.
        while heap and not heap[0][VALID]:
            heappop(heap)

    current = best
    return best[PARENT] is not None

