"""
장애물(건물 등) 회피 경로탐색 — 그리드 A*.
좌표계: km, 원점=중심자산 (engine.ASSETS와 동일).

obstacles: 건물 등 장애물 폴리곤 리스트. 각 폴리곤은 [(x1,y1),(x2,y2),...] (km).
실제 지도(건물 폴리곤) 데이터는 별도 프로젝트 병합 후 주입될 예정 — 그 전까지는
obstacles=None/[] 이면 자동으로 직선 경로(목표점 직행)로 폴백하므로 기존 동작과 동일하다.
"""
import heapq
import numpy as np

DEFAULT_RESOLUTION = 0.05   # km/cell (50m)
_NEIGHBORS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _point_in_polygon(x, y, poly):
    """레이캐스팅 point-in-polygon"""
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            x_intersect = (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
            if x < x_intersect:
                inside = not inside
        j = i
    return inside


def _point_in_any_polygon(x, y, obstacles):
    return any(_point_in_polygon(x, y, poly) for poly in obstacles)


def build_occupancy_grid(obstacles, bounds, resolution=DEFAULT_RESOLUTION):
    """bounds=(xmin,xmax,ymin,ymax) 내부를 격자화, 장애물 폴리곤 내부 셀을 True(점유)로 표시"""
    xmin, xmax, ymin, ymax = bounds
    nx = max(1, int(np.ceil((xmax - xmin) / resolution)))
    ny = max(1, int(np.ceil((ymax - ymin) / resolution)))
    grid = np.zeros((nx, ny), dtype=bool)
    if not obstacles:
        return grid
    for i in range(nx):
        x = xmin + (i + 0.5) * resolution
        for j in range(ny):
            y = ymin + (j + 0.5) * resolution
            grid[i, j] = _point_in_any_polygon(x, y, obstacles)
    return grid


def _xy_to_idx(x, y, bounds, resolution):
    xmin, xmax, ymin, ymax = bounds
    nx = max(1, int(np.ceil((xmax - xmin) / resolution)))
    ny = max(1, int(np.ceil((ymax - ymin) / resolution)))
    i = int(np.clip((x - xmin) / resolution, 0, nx - 1))
    j = int(np.clip((y - ymin) / resolution, 0, ny - 1))
    return i, j


def _idx_to_xy(i, j, bounds, resolution):
    xmin, xmax, ymin, ymax = bounds
    return xmin + (i + 0.5) * resolution, ymin + (j + 0.5) * resolution


def _astar_grid(grid, start, goal):
    nx, ny = grid.shape

    def h(a, b):
        return float(np.hypot(a[0] - b[0], a[1] - b[1]))

    open_heap = [(h(start, goal), 0.0, start)]
    came_from = {}
    gscore = {start: 0.0}
    visited = set()
    while open_heap:
        _, g, cur = heapq.heappop(open_heap)
        if cur in visited:
            continue
        visited.add(cur)
        if cur == goal:
            path = [cur]
            while path[-1] in came_from:
                path.append(came_from[path[-1]])
            return path[::-1]
        for dx, dy in _NEIGHBORS:
            ni, nj = cur[0] + dx, cur[1] + dy
            if not (0 <= ni < nx and 0 <= nj < ny) or grid[ni, nj]:
                continue
            neighbor = (ni, nj)
            ng = g + h(cur, neighbor)
            if ng < gscore.get(neighbor, float("inf")):
                gscore[neighbor] = ng
                came_from[neighbor] = cur
                heapq.heappush(open_heap, (ng + h(neighbor, goal), ng, neighbor))
    return None  # 경로 없음(완전히 막힘)


def _line_of_sight(grid, a, b):
    """a-b 그리드 셀 사이 직선상에 장애물이 있는지 샘플링 확인 (경로 스무딩용)"""
    nx, ny = grid.shape
    n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) * 2 + 1
    for t in np.linspace(0, 1, n):
        i = int(round(a[0] + (b[0] - a[0]) * t))
        j = int(round(a[1] + (b[1] - a[1]) * t))
        if not (0 <= i < nx and 0 <= j < ny) or grid[i, j]:
            return False
    return True


def _smooth(grid, path):
    """불필요한 지그재그 웨이포인트 제거 (시야가 트인 지점끼리 직결)"""
    if len(path) < 3:
        return path
    smoothed = [path[0]]
    i = 0
    while i < len(path) - 1:
        j = len(path) - 1
        while j > i + 1 and not _line_of_sight(grid, path[i], path[j]):
            j -= 1
        smoothed.append(path[j])
        i = j
    return smoothed


def plan_path(start_xy, goal_xy, obstacles=None, bounds=None, resolution=DEFAULT_RESOLUTION):
    """start_xy/goal_xy: (x,y) km. obstacles 없으면 직선 폴백.
    반환: [(x,y), ...] 웨이포인트 리스트 (시작점 미포함, 목표점 포함, 최소 1개).
    """
    if not obstacles:
        return [tuple(goal_xy)]
    if bounds is None:
        xs = [start_xy[0], goal_xy[0]] + [p[0] for poly in obstacles for p in poly]
        ys = [start_xy[1], goal_xy[1]] + [p[1] for poly in obstacles for p in poly]
        pad = 0.3
        bounds = (min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad)
    grid = build_occupancy_grid(obstacles, bounds, resolution)
    start_idx = _xy_to_idx(start_xy[0], start_xy[1], bounds, resolution)
    goal_idx = _xy_to_idx(goal_xy[0], goal_xy[1], bounds, resolution)
    if grid[start_idx] or grid[goal_idx]:
        return [tuple(goal_xy)]   # 시작/목표가 장애물 내부 → 경로탐색 불가, 직선 폴백
    path = _astar_grid(grid, start_idx, goal_idx)
    if not path:
        return [tuple(goal_xy)]   # 완전히 막힘 → 직선 폴백
    path = _smooth(grid, path)
    waypoints = [_idx_to_xy(i, j, bounds, resolution) for i, j in path[1:]]
    if not waypoints:
        return [tuple(goal_xy)]
    waypoints[-1] = tuple(goal_xy)   # 마지막 웨이포인트는 목표점에 정확히 스냅
    return waypoints


def advance_along_path(p, waypoints, wp_idx, budget):
    """현재 위치 p에서 남은 이동거리 budget(km)만큼 웨이포인트를 따라 전진.
    한 스텝에 여러 웨이포인트를 통과할 수 있음. 목표 도달 후에는 그 자리에 정지(체공/명중).
    반환: (새 위치, 갱신된 wp_idx)
    """
    p = np.array(p, dtype=float)
    n = len(waypoints)
    while budget > 1e-9 and wp_idx < n:
        goal = np.array(waypoints[wp_idx])
        to_goal = goal - p
        dist = float(np.linalg.norm(to_goal))
        if dist < 1e-9:
            wp_idx += 1
            continue
        if budget >= dist:
            p = goal
            budget -= dist
            wp_idx += 1
        else:
            p = p + to_goal / dist * budget
            budget = 0.0
    return p, min(wp_idx, n - 1)
