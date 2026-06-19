from app.services.optimizer import optimize_open_route, route_cost, two_opt_open_path


def test_optimizer_keeps_start_and_improves_simple_route():
    matrix = [
        [0, 10, 2, 2],
        [10, 0, 2, 2],
        [2, 2, 0, 10],
        [2, 2, 10, 0],
    ]
    original = [0, 1, 2, 3]
    optimized = optimize_open_route(matrix, start=0)
    assert optimized[0] == 0
    assert sorted(optimized) == [0, 1, 2, 3]
    assert route_cost(optimized, matrix) <= route_cost(original, matrix)


def test_two_opt_handles_asymmetric_matrix_without_route_regression():
    # Asymmetric matrix: A->B can differ from B->A. The optimized route must
    # preserve all nodes, keep the start fixed, and not increase route cost.
    matrix = [
        [0, 8, 2, 9, 9],
        [3, 0, 8, 2, 9],
        [2, 6, 0, 8, 2],
        [9, 2, 6, 0, 8],
        [8, 9, 2, 6, 0],
    ]
    initial = [0, 1, 2, 3, 4]
    optimized = optimize_open_route(matrix, start=0)

    assert optimized[0] == 0
    assert sorted(optimized) == [0, 1, 2, 3, 4]
    assert route_cost(optimized, matrix) <= route_cost(initial, matrix)


def test_two_opt_delta_matches_naive_two_opt_for_asymmetric_matrix():
    def naive_two_opt(order, matrix, max_iterations=1500):
        best = order[:]
        best_cost = route_cost(best, matrix)
        improved = True
        iterations = 0
        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            for i in range(1, len(best) - 2):
                for k in range(i + 1, len(best) - 1):
                    candidate = best[:i] + list(reversed(best[i : k + 1])) + best[k + 1 :]
                    candidate_cost = route_cost(candidate, matrix)
                    if candidate_cost + 1e-9 < best_cost:
                        best = candidate
                        best_cost = candidate_cost
                        improved = True
                        break
                if improved:
                    break
        return best

    matrix = [
        [0, 11, 3, 8, 9, 7],
        [5, 0, 10, 2, 6, 4],
        [7, 4, 0, 12, 3, 5],
        [8, 3, 9, 0, 11, 2],
        [6, 7, 2, 5, 0, 10],
        [3, 8, 6, 4, 5, 0],
    ]
    order = [0, 2, 4, 5, 3, 1]

    optimized = two_opt_open_path(order, matrix)
    expected = naive_two_opt(order, matrix)

    assert optimized == expected
    assert route_cost(optimized, matrix) == route_cost(expected, matrix)
