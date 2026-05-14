# Copyright (c) 2026 Francois ND and the Piqueserver Authors

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

"""Per-protocol-extension policy registry.

Scripts call ``protocol.extensions.enable(...)`` / ``.mandate(...)`` /
``.disable(...)`` to declare what the server speaks. The registry keeps a
single state per extension and applies a priority rule so that two scripts
can coexist without trampling each other's intent:

* ``DISABLED`` is a veto. Going ``DISABLED <-> ENABLED|MANDATORY`` raises.
* For the ``ENABLED``/``MANDATORY`` pair, the stricter state wins. A later
  ``mandate`` over an ``enable`` upgrades; a later ``enable`` over a
  ``mandate`` is silently dropped (the stronger commitment stands).
* Re-asserting the same state simply refreshes the reason/version.
"""

from typing import Dict, List, Optional, Tuple

from twisted.logger import Logger

from pyspades.constants import EXTENSION_NAMES

log = Logger()

ENABLED = "enabled"
MANDATORY = "mandatory"
DISABLED = "disabled"

_RANK = {DISABLED: 0, ENABLED: 1, MANDATORY: 2}


class ProtoExtensionPolicyConflict(RuntimeError):
    """Raised when a registry call would weaken an existing commitment.

    Specifically: any transition that crosses the ``DISABLED`` boundary.
    Same-state re-assertions and ``ENABLED`` <-> ``MANDATORY`` moves are
    handled silently.
    """


def _name(ext_id: int) -> str:
    return EXTENSION_NAMES.get(ext_id, "id {}".format(ext_id))


class ProtoExtensionRegistry:
    def __init__(self) -> None:
        # ext_id -> (state, version, reason)
        self._policies: Dict[int, Tuple[str, int, str]] = {}

    def enable(self, ext_id: int, reason: str, version: int = 1) -> None:
        self._set(ext_id, ENABLED, version, reason)

    def mandate(self, ext_id: int, reason: str, version: int = 1) -> None:
        self._set(ext_id, MANDATORY, version, reason)

    def disable(self, ext_id: int, reason: str) -> None:
        self._set(ext_id, DISABLED, 0, reason)

    def policy_of(self, ext_id: int) -> Optional[str]:
        entry = self._policies.get(ext_id)
        return entry[0] if entry else None

    def advertised(self) -> List[Tuple[int, int]]:
        return [(ext_id, ver)
                for ext_id, (state, ver, _) in self._policies.items()
                if state in (ENABLED, MANDATORY)]

    def mandatory(self) -> List[Tuple[int, int, str, str]]:
        return [(ext_id, ver, reason, _name(ext_id))
                for ext_id, (state, ver, reason) in self._policies.items()
                if state == MANDATORY]

    def enabled_only(self) -> List[Tuple[int, int, str, str]]:
        return [(ext_id, ver, reason, _name(ext_id))
                for ext_id, (state, ver, reason) in self._policies.items()
                if state == ENABLED]

    def policies(self) -> Dict[int, Tuple[str, int, str]]:
        return dict(self._policies)

    def _set(self, ext_id: int, new_state: str, version: int,
             reason: str) -> None:
        existing = self._policies.get(ext_id)
        if existing is None:
            self._policies[ext_id] = (new_state, version, reason)
            return

        prev_state, prev_version, prev_reason = existing

        # the DISABLED veto cannot coexist with an active state in either
        # direction. catch the bug at boot rather than guessing what the
        # author meant.
        if (new_state == DISABLED) != (prev_state == DISABLED):
            raise ProtoExtensionPolicyConflict(
                "cannot {new} extension {name!r}: previously {prev} with "
                "reason: {prev_reason!r}; new reason: {reason!r}".format(
                    new=new_state, prev=prev_state,
                    name=_name(ext_id),
                    prev_reason=prev_reason, reason=reason))

        if new_state == DISABLED:
            # both DISABLED: idempotent refresh.
            self._policies[ext_id] = (DISABLED, 0, reason)
            return

        # both in {ENABLED, MANDATORY}: stricter state wins.
        if _RANK[new_state] > _RANK[prev_state]:
            log.debug(
                "extension {name!r} upgraded {prev}->{new}; reason replaced",
                name=_name(ext_id), prev=prev_state, new=new_state)
            self._policies[ext_id] = (new_state, version, reason)
        elif _RANK[new_state] == _RANK[prev_state]:
            # same level: latest assertion overwrites reason/version.
            self._policies[ext_id] = (new_state, version, reason)
        else:
            # MANDATORY beats a later ENABLED: keep the stronger commitment.
            log.debug(
                "extension {name!r} kept {prev}; ignoring later {new} "
                "(reason: {reason!r})",
                name=_name(ext_id), prev=prev_state, new=new_state,
                reason=reason)
