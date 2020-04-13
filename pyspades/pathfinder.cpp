#include <Python.h>
#include <bitset>
#include <math.h>
#include <vector>
#include <iostream>
#include <queue> 
#include "vxl_c.h"

struct Tnode {
    float cost, full_cost;
    int x, y, z;
    uint32_t prev;
};

// Никогда не проверяет начальную точку
float inline get_cost(int x1, int y1, int z1, int x2, int y2, int z2, int can_dig, int can_build, MapData *map) {
    #define solid(x, y, z) (map->geometry[get_pos(x, y, z)])
    // Если ставим под собой блок
    if (can_build && (x1 == x2) && (y1 == y2) && (z1 > z2)) return 3.2;
    // Проверка основования под целевой точкой
    if (!solid(x2, y2, z2 + 3)) return -1;
    // Если копаем под себя
    if (can_dig && (x1 == x2) && (y1 == y2) && (z1 < z2)) return 4;
    // Проверка целевой точки на 3 свбодных блока
    if (solid(x2, y2, z2) || solid(x2, y2, z2 + 1) || solid(x2, y2, z2 + 2)) return -1;
    // Движемся по диагонали
    if ((x1 != x2) && (y1 != y2)) {
        int z = std::min(z1, z2);
        // При движении по диагонали оба боковых столба должны быть свбодны
        if (solid(x1, y2, z) or solid(x1, y2, z + 1) or solid(x1, y2, z + 2) or
            solid(x2, y1, z) or solid(x2, y1, z + 1) or solid(x2, y1, z + 2)) return -1;
        return (z1 != z2) ? 1.7320508 : 1.414;
    };
    // Движемся не по диагонали
    return (z1 != z2) ? 1.4142136 : 1;
}

float inline distance(int x1, int y1, int z1, int x2, int y2, int z2) {
    int dx = x1 - x2;
    int dy = y1 - y2;
    int dz = z1 - z2;
    return sqrt(dx*dx + dy*dy + dz*dz);
}

int inline is_valid(int x, int y, int z)
{
    return (uint32_t)x < 512 && (uint32_t)y < 512 && (uint32_t)z < 64;
}

PyObject* a_star(int x1, int y1, int z1, int x2, int y2, int z2, int can_dig, int can_build, MapData *map) {
    priority_queue <pair<float, uint32_t>> open;
    std::bitset<MAP_X * MAP_Y * MAP_Z> visited;
    std::vector<Tnode> nodes;

    PyObject* integer;
    PyObject* tuple;
    PyObject* list = PyList_New(0);

    // First node
    Tnode node;
    node.prev = 4294967295;
    node.x = x1;
    node.y = y1;
    node.z = z1;
    node.cost = 0;
    node.full_cost = 0;
    nodes.push_back(node);
    visited[get_pos(x1, y1, z1)] = true;
    open.push(make_pair(0, 0));

    int j = 0;
    Tnode best;
    int best_score = 999999;
    while (!open.empty()) {
        ++j;

        uint32_t id = open.top().second;
        open.pop();
        //std::cout << id << std::endl;
        node = nodes[id];

        /*
        tuple = PyTuple_New(3);
        integer = PyLong_FromLong(node.x);
        PyTuple_SetItem(tuple, 0, integer);
        integer = PyLong_FromLong(node.y);
        PyTuple_SetItem(tuple, 1, integer);
        integer = PyLong_FromLong(node.z);
        PyTuple_SetItem(tuple, 2, integer);
        PyList_Append(list, tuple);
        */

        for (int dx = -1; dx <= 1; ++dx)
        for (int dy = -1; dy <= 1; ++dy)
        for (int dz = -1; dz <= 1; ++dz)
        {
            int x = node.x + dx;
            int y = node.y + dy;
            int z = node.z + dz;

            if (!is_valid(x, y, z + 3)) continue;
            if (z < 0) continue;
            if (visited[get_pos(x, y, z)]) continue;

            float cost = get_cost(node.x, node.y, node.z, x, y, z, can_dig, can_build, map);
            if (cost == -1) continue;

            float dist = distance(x, y, z, x2, y2, z2);
            if (dist < best_score) {
                best_score = dist;
                best = node;
                if (dist < 0.1) goto loop_end;
            }

            Tnode new_node;
            new_node.prev = id;
            new_node.x = x;
            new_node.y = y;
            new_node.z = z;
            new_node.cost = cost;
            new_node.full_cost = node.full_cost + cost;
            nodes.push_back(new_node);
            visited[get_pos(x, y, z)] = true;

            open.push(make_pair(-1*(dist + new_node.full_cost), nodes.size() - 1));
        }
    }
    loop_end: 

    //std::cout << "END " << j << std::endl;
    //std::cout << "COST " << best.full_cost  << std::endl;
    //std::cout << "DIST " << distance(best.x, best.y, best.z, x2, y2, z2) << std::endl;

    nodes.clear();

    //PyObject* integer;
    //PyObject* tuple;
    //PyObject* list = PyList_New(0);
    while (best.prev != 4294967295) {
        tuple = PyTuple_New(3);
        integer = PyLong_FromLong(best.x);
        PyTuple_SetItem(tuple, 0, integer);
        integer = PyLong_FromLong(best.y);
        PyTuple_SetItem(tuple, 1, integer);
        integer = PyLong_FromLong(best.z);
        PyTuple_SetItem(tuple, 2, integer);
        PyList_Append(list, tuple);
        best = nodes[best.prev];
    }
    return list;
}