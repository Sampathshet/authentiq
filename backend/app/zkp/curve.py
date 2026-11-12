import hashlib

BASE_FIELD_PRIME = 21888242871839275222246405745257275088696311157297823662689037894645226208583
SCALAR_FIELD_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617
CURVE_B = 3
GENERATOR = (1, 2)


def inverse(value: int, modulus: int) -> int:
    return pow(value % modulus, -1, modulus)


def is_on_curve(point: tuple[int, int] | None) -> bool:
    if point is None:
        return True
    x, y = point
    return (y * y - (x * x * x + CURVE_B)) % BASE_FIELD_PRIME == 0


def point_add(left: tuple[int, int] | None, right: tuple[int, int] | None) -> tuple[int, int] | None:
    if left is None:
        return right
    if right is None:
        return left
    x1, y1 = left
    x2, y2 = right
    if x1 == x2 and (y1 + y2) % BASE_FIELD_PRIME == 0:
        return None
    if left == right:
        slope = (3 * x1 * x1 * inverse(2 * y1, BASE_FIELD_PRIME)) % BASE_FIELD_PRIME
    else:
        slope = ((y2 - y1) * inverse(x2 - x1, BASE_FIELD_PRIME)) % BASE_FIELD_PRIME
    x3 = (slope * slope - x1 - x2) % BASE_FIELD_PRIME
    y3 = (slope * (x1 - x3) - y1) % BASE_FIELD_PRIME
    return x3, y3


def point_negate(point: tuple[int, int] | None) -> tuple[int, int] | None:
    if point is None:
        return None
    return point[0], (-point[1]) % BASE_FIELD_PRIME


def point_sub(left, right):
    return point_add(left, point_negate(right))


def scalar_mul(scalar: int, point: tuple[int, int] | None) -> tuple[int, int] | None:
    scalar %= SCALAR_FIELD_PRIME
    result = None
    addend = point
    while scalar:
        if scalar & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        scalar >>= 1
    return result


def point_to_hex(point: tuple[int, int] | None) -> str:
    if point is None:
        return "0x" + "0" * 128
    x, y = point
    return "0x" + format(x, "064x") + format(y, "064x")


def point_from_hex(value: str) -> tuple[int, int]:
    raw = value[2:] if value.startswith("0x") else value
    if len(raw) != 128:
        raise ValueError("Point encoding must contain 128 hex characters")
    x = int(raw[:64], 16)
    y = int(raw[64:], 16)
    if x >= BASE_FIELD_PRIME or y >= BASE_FIELD_PRIME or not is_on_curve((x, y)):
        raise ValueError("Point is not on the BN254 curve")
    return x, y


def hash_to_curve(label: str) -> tuple[int, int]:
    counter = 0
    while True:
        digest = hashlib.sha256(f"{label}:{counter}".encode("utf-8")).digest()
        x = int.from_bytes(digest, "big") % BASE_FIELD_PRIME
        rhs = (pow(x, 3, BASE_FIELD_PRIME) + CURVE_B) % BASE_FIELD_PRIME
        y = pow(rhs, (BASE_FIELD_PRIME + 1) // 4, BASE_FIELD_PRIME)
        if (y * y) % BASE_FIELD_PRIME == rhs:
            point = (x, y)
            if is_on_curve(point) and point != GENERATOR:
                return point
        counter += 1
