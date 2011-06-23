cdef inline int check_default_int(int value, int default) except -1:
    if value != default:
        raw_input('check_default() failed')
        raise NotImplementedError('was %s, should be %s' % (value, default))
    return 0