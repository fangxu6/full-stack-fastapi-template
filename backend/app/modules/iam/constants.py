from collections.abc import Mapping  # noqa: I001


PLATFORM_ADMINISTRATOR = "platform_administrator"
INVENTORY_OPERATOR = "inventory_operator"
INVENTORY_VIEWER = "inventory_viewer"

PERMISSIONS: tuple[tuple[str, str, str, str], ...] = (
    ("system.users.read", "System", "View users", "View user accounts and roles."),
    (
        "system.users.manage",
        "System",
        "Manage users",
        "Create, update, and delete user accounts.",
    ),
    (
        "iam.roles.read",
        "Access control",
        "View roles",
        "View roles and the permission catalog.",
    ),
    (
        "iam.roles.manage",
        "Access control",
        "Manage roles",
        "Create and maintain custom roles.",
    ),
    (
        "inventory.masters.read",
        "Inventory",
        "View master data",
        "View processing and receiving units.",
    ),
    (
        "inventory.masters.manage",
        "Inventory",
        "Manage master data",
        "Create and update processing and receiving units.",
    ),
    (
        "inventory.documents.read",
        "Inventory",
        "View documents",
        "View inventory documents.",
    ),
    (
        "inventory.documents.manage",
        "Inventory",
        "Manage documents",
        "Create, update, delete, and restore inventory documents.",
    ),
    (
        "inventory.balances.read",
        "Inventory",
        "View balances",
        "View current inventory balances.",
    ),
    (
        "inventory.ledger.read",
        "Inventory",
        "View ledger",
        "View inventory ledger entries.",
    ),
)

PERMISSION_CODES = frozenset(permission[0] for permission in PERMISSIONS)
GOVERNANCE_PERMISSION_PREFIXES = ("system.users.", "iam.roles.")
PREREQUISITES: Mapping[str, frozenset[str]] = {
    "system.users.manage": frozenset({"system.users.read", "iam.roles.read"}),
    "iam.roles.manage": frozenset({"iam.roles.read"}),
    "inventory.masters.manage": frozenset({"inventory.masters.read"}),
    "inventory.documents.manage": frozenset({"inventory.documents.read"}),
}

BUILTIN_ROLES: Mapping[str, tuple[str, str, frozenset[str]]] = {
    PLATFORM_ADMINISTRATOR: (
        "Platform Administrator",
        "Full platform administration access.",
        PERMISSION_CODES,
    ),
    INVENTORY_OPERATOR: (
        "Inventory Operator",
        "Create and manage inventory masters and documents.",
        frozenset(code for code in PERMISSION_CODES if code.startswith("inventory.")),
    ),
    INVENTORY_VIEWER: (
        "Inventory Viewer",
        "Read inventory masters, documents, balances, and ledger entries.",
        frozenset(
            {
                "inventory.masters.read",
                "inventory.documents.read",
                "inventory.balances.read",
                "inventory.ledger.read",
            }
        ),
    ),
}


def is_governance_permission(permission_code: str) -> bool:
    return permission_code.startswith(GOVERNANCE_PERMISSION_PREFIXES)
