from __future__ import annotations


_EPSILON = 1e-9


def route_cost(order: list[int], matrix: list[list[float]]) -> float:
    return sum(matrix[a][b] for a, b in zip(order, order[1:]))


def nearest_neighbor_path(matrix: list[list[float]], start: int = 0) -> list[int]:
    n = len(matrix)
    if n <= 1:
        return list(range(n))
    unvisited = set(range(n))
    order = [start]
    unvisited.remove(start)
    current = start
    while unvisited:
        nxt = min(unvisited, key=lambda node: matrix[current][node])
        order.append(nxt)
        unvisited.remove(nxt)
        current = nxt
    return order


def _two_opt_delta(order: list[int], matrix: list[list[float]], i: int, k: int) -> float:
    """Return route-cost delta for reversing order[i:k+1].

    OSRM road matrices can be asymmetric: distance A→B may differ from B→A.
    Therefore, reversing a segment changes the left boundary, the internal edge
    directions and, when the segment is not the tail, the right boundary too.

    For an open route only the first node is fixed. The last node is not a depot
    by default, so 2-opt must also be allowed to reverse a tail segment where
    ``k`` is the final index.
    """
    before = order[i - 1]
    first = order[i]
    last = order[k]
    after = order[k + 1] if k + 1 < len(order) else None

    old_boundary = matrix[before][first]
    new_boundary = matrix[before][last]
    if after is not None:
        old_boundary += matrix[last][after]
        new_boundary += matrix[first][after]

    old_internal = sum(matrix[order[x]][order[x + 1]] for x in range(i, k))
    new_internal = sum(matrix[order[x + 1]][order[x]] for x in range(i, k))
    return (new_boundary + new_internal) - (old_boundary + old_internal)


def two_opt_open_path(order: list[int], matrix: list[list[float]], max_iterations: int = 1500) -> list[int]:
    best = order[:]
    improved = True
    iterations = 0

    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        # Keep only the first node fixed; the final point is allowed to move
        # because this is an open route unless a depot/end point is modelled explicitly.
        for i in range(1, len(best) - 1):
            for k in range(i + 1, len(best)):
                delta = _two_opt_delta(best, matrix, i, k)
                if delta < -_EPSILON:
                    best[i : k + 1] = reversed(best[i : k + 1])
                    improved = True
                    break
            if improved:
                break

    return best


def optimize_open_route(distance_matrix: list[list[float]], start: int = 0) -> list[int]:
    initial = nearest_neighbor_path(distance_matrix, start=start)
    return two_opt_open_path(initial, distance_matrix)
