#ifndef COMMON_C_H
#define COMMON_C_H

struct Vector
{
    float x, y, z;
};

struct LongVector
{
    long x, y, z;
};

inline Vector * create_vector(float x, float y, float z)
{
    Vector * v = new Vector;
    v->x = x; v->y = y; v->z = z;
    return v;
}

inline void destroy_vector(Vector * v)
{
    delete v;
}

#endif /* COMMON_C_H */