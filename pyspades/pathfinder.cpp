#include <Python.h>
#include "structmember.h"
#include <bitset>
#include <math.h>
#include <vector>
#include <iostream>
#include <queue> 
#include "vxl_c.h"
#include <thread>
#include <future>

using namespace std;

struct Tnode {
    float cost, full_cost;
    int x, y, z;
    uint32_t prev;
};

float inline distance(int x1, int y1, int z1, int x2, int y2, int z2) {
    int dx = x1 - x2;
    int dy = y1 - y2;
    int dz = z1 - z2;
    //return sqrt(dx*dx + dy*dy + dz*dz);
    return abs(dx) + abs(dy) + abs(dz) + abs(dx-dy) + abs(dx-dz) + abs(dy-dz);
}

int inline is_valid(int x, int y, int z)
{
    return (uint32_t)x < 512 && (uint32_t)y < 512 && (uint32_t)z < 64;
}

const float dist_diag_z = distance(0, 0, 0, 1, 1, 1);
const float dist_diag = distance(0, 0, 0, 1, 1, 0);
const float straight_z = distance(0, 0, 0, 1, 0, 1);
const float straight = distance(0, 0, 0, 1, 0, 0);
const float build_one = dist_diag_z * 1.5;
const float dig_one = dist_diag_z * 2.7;
// Никогда не проверяет начальную точку
float inline get_cost(int x1, int y1, int z1, int x2, int y2, int z2, int can_dig, int can_build, MapData *map) {
    #define solid(x, y, z) (map->geometry[get_pos(x, y, z)])
    // Если ставим под собой блок
    if (can_build && (x1 == x2) && (y1 == y2) && (z1 > z2)) return build_one;
    // Проверка основания под целевой точкой
    if (!solid(x2, y2, z2 + 3)) return -1;
    // Если копаем под себя
    if (can_dig && (x1 == x2) && (y1 == y2) && (z1 < z2)) return dig_one;
    // Проверка целевой точки на 3 свободных блока
    if (solid(x2, y2, z2) || solid(x2, y2, z2 + 1) || solid(x2, y2, z2 + 2)) return -1;
    // Движемся по диагонали
    if ((x1 != x2) && (y1 != y2)) {
        int z = std::min(z1, z2);
        // При движении по диагонали оба боковых столба должны быть свбодными
        if (solid(x1, y2, z) or solid(x1, y2, z + 1) or solid(x1, y2, z + 2) or
            solid(x2, y1, z) or solid(x2, y1, z + 1) or solid(x2, y1, z + 2)) return -1;
        return (z1 != z2) ? dist_diag_z : dist_diag;
    };
    // Движемся не по диагонали
    return (z1 != z2) ? straight_z : straight;
}

PyObject* a_star_real(int x1, int y1, int z1, int x2, int y2, int z2, int can_dig, int can_build, MapData *map) {
    priority_queue <pair<float, uint32_t>> open;
    std::bitset<MAP_X * MAP_Y * MAP_Z> visited;
    std::vector<Tnode> nodes;
    /*
    PyObject* integer;
    PyObject* tuple;
    PyObject* list = PyList_New(0);
    */
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

    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
    PyObject* integer;
    PyObject* tuple;
    PyObject* list = PyList_New(0);
    
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
    PyGILState_Release(gstate);

    nodes.clear();
    return list;
}

///////////////////////////////////////////////////////////////////////////////

typedef struct {
    PyObject_HEAD
    std::future<PyObject*> future;
} AStarFutureData;

PyObject* a_star_ready(AStarFutureData *self, PyObject *Py_UNUSED(ignored)) {
    if (self->future.wait_for(chrono::seconds(0)) == future_status::ready) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
};

PyObject* a_star_get(AStarFutureData *self, PyObject *Py_UNUSED(ignored)) {
    //Py_BEGIN_ALLOW_THREADS
    PyThreadState *_save;
    _save = PyEval_SaveThread();

    auto list = self->future.get();

    //Py_END_ALLOW_THREADS
    PyEval_RestoreThread(_save);

    PyObject* reverse = PyObject_GetAttrString(list, (char*)"reverse");
    PyObject_CallObject(reverse, nullptr);
    return list;
};

static PyMethodDef AStarFuture_methods[] = {
    {"ready", (PyCFunction) a_star_ready, METH_NOARGS, "Checks if the result available"},
    {"get", (PyCFunction) a_star_get, METH_NOARGS, "Returns the result"},
    {NULL}  /* Sentinel */
};

static PyTypeObject AStarFutureType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "AStarFuture",
    .tp_basicsize = sizeof(AStarFutureData),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_methods = AStarFuture_methods,
    .tp_new = PyType_GenericNew,
};

bool registred = false;
PyObject* a_star_start(int x1, int y1, int z1, int x2, int y2, int z2, int can_dig, int can_build, MapData *map) {
    if (!registred) {
        PyType_Ready(&AStarFutureType);
        registred = true;
    };
    PyObject *object =  PyObject_CallObject((PyObject *) &AStarFutureType, nullptr);
    ((AStarFutureData*)object)->future =  std::async(a_star_real, x1, y1, z1, x2, y2, z2, can_dig, can_build, map);
    return object;
}