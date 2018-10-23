import numpy as np

def VAL2RADIAN(val):
    return (val - 2048) * 0.088 * np.pi / 180

def RADIAN2VAL(rad):
    return rad * 180 / np.pi / 0.088 + 2048

JOINT_LOW_BOUND_VAL = np.array([
    0, 700, 1400, 0, 1600, 1000,
    1346, 1850,
    1800, 1400, 1800, 1000, 1200, 1850,1800, 2048, 1000, 2048, 1500, 1700
])

JOINT_UP_BOUND_VAL = np.array([
    4095, 2400, 3000, 4095, 3400, 2800,
    2632, 2600,
    2200, 2048, 3100, 2048, 2500, 2400, 2200, 2600, 2300, 3100, 2800, 2300
])

JOINT_LOW_BOUND = VAL2RADIAN(JOINT_LOW_BOUND_VAL)


JOINT_UP_BOUND = VAL2RADIAN(JOINT_UP_BOUND_VAL)


