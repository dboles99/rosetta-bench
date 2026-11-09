def _validate(matrix):
    if not matrix:
        return 0, 0
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise ValueError("ragged matrix")
    return len(matrix), width


def spiral_order(matrix):
    rows, cols = _validate(matrix)
    if rows == 0 or cols == 0:
        return []
    out = []
    top, bottom, left, right = 0, rows - 1, 0, cols - 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            out.append(matrix[top][c])
        for r in range(top + 1, bottom + 1):
            out.append(matrix[r][right])
        if top < bottom:
            for c in range(right - 1, left - 1, -1):
                out.append(matrix[bottom][c])
        if left < right:
            for r in range(bottom - 1, top, -1):
                out.append(matrix[r][left])
        top, bottom, left, right = top + 1, bottom - 1, left + 1, right - 1
    return out


def rotate(matrix, k=1):
    rows, cols = _validate(matrix)
    if rows == 0 or cols == 0:
        return []
    result = [list(row) for row in matrix]
    for _ in range(k % 4):
        result = [list(row) for row in zip(*result[::-1])]
    return result
