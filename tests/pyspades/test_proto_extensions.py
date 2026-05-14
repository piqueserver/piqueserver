"""tests for pyspades/proto_extensions.py"""

from twisted.trial import unittest

from pyspades.constants import EXTENSION_CHATTYPE, EXTENSION_KICKREASON
from pyspades.proto_extensions import (
    DISABLED, ENABLED, MANDATORY,
    ProtoExtensionPolicyConflict, ProtoExtensionRegistry,
)


class ProtoExtensionRegistryTest(unittest.TestCase):
    def test_enable_then_reenable_updates_reason(self):
        reg = ProtoExtensionRegistry()
        reg.enable(EXTENSION_CHATTYPE, "first")
        reg.enable(EXTENSION_CHATTYPE, "second", version=2)
        policies = reg.policies()
        self.assertEqual(policies[EXTENSION_CHATTYPE], (ENABLED, 2, "second"))

    def test_enable_then_mandate_upgrades(self):
        reg = ProtoExtensionRegistry()
        reg.enable(EXTENSION_KICKREASON, "QoL")
        reg.mandate(EXTENSION_KICKREASON, "competitive mode needs it")
        self.assertEqual(reg.policy_of(EXTENSION_KICKREASON), MANDATORY)
        mandatory = reg.mandatory()
        self.assertEqual(len(mandatory), 1)
        ext_id, ver, reason, name = mandatory[0]
        self.assertEqual(ext_id, EXTENSION_KICKREASON)
        self.assertEqual(reason, "competitive mode needs it")

    def test_mandate_then_enable_stays_mandatory(self):
        reg = ProtoExtensionRegistry()
        reg.mandate(EXTENSION_KICKREASON, "strict policy")
        reg.enable(EXTENSION_KICKREASON, "tried to weaken")
        self.assertEqual(reg.policy_of(EXTENSION_KICKREASON), MANDATORY)
        # mandate reason preserved, the later enable was discarded
        ext_id, ver, reason, name = reg.mandatory()[0]
        self.assertEqual(reason, "strict policy")

    def test_mandate_then_mandate_updates_reason(self):
        reg = ProtoExtensionRegistry()
        reg.mandate(EXTENSION_KICKREASON, "first")
        reg.mandate(EXTENSION_KICKREASON, "second")
        ext_id, ver, reason, name = reg.mandatory()[0]
        self.assertEqual(reason, "second")

    def test_disable_after_enable_raises(self):
        reg = ProtoExtensionRegistry()
        reg.enable(EXTENSION_CHATTYPE, "QoL")
        self.assertRaises(ProtoExtensionPolicyConflict,
                          reg.disable, EXTENSION_CHATTYPE, "veto")

    def test_disable_after_mandate_raises(self):
        reg = ProtoExtensionRegistry()
        reg.mandate(EXTENSION_KICKREASON, "needed")
        self.assertRaises(ProtoExtensionPolicyConflict,
                          reg.disable, EXTENSION_KICKREASON, "veto")

    def test_enable_after_disable_raises(self):
        reg = ProtoExtensionRegistry()
        reg.disable(EXTENSION_CHATTYPE, "veto")
        self.assertRaises(ProtoExtensionPolicyConflict,
                          reg.enable, EXTENSION_CHATTYPE, "QoL")

    def test_mandate_after_disable_raises(self):
        reg = ProtoExtensionRegistry()
        reg.disable(EXTENSION_KICKREASON, "veto")
        self.assertRaises(ProtoExtensionPolicyConflict,
                          reg.mandate, EXTENSION_KICKREASON, "needed")

    def test_disable_idempotent(self):
        reg = ProtoExtensionRegistry()
        reg.disable(EXTENSION_CHATTYPE, "first reason")
        reg.disable(EXTENSION_CHATTYPE, "second reason")
        self.assertEqual(reg.policy_of(EXTENSION_CHATTYPE), DISABLED)

    def test_advertised_lists_enabled_and_mandatory(self):
        reg = ProtoExtensionRegistry()
        reg.enable(EXTENSION_CHATTYPE, "QoL", version=1)
        reg.mandate(EXTENSION_KICKREASON, "needed", version=2)
        ids = sorted(ext_id for ext_id, _ in reg.advertised())
        self.assertEqual(ids, sorted([EXTENSION_CHATTYPE,
                                      EXTENSION_KICKREASON]))

    def test_enabled_only_excludes_mandatory(self):
        reg = ProtoExtensionRegistry()
        reg.enable(EXTENSION_CHATTYPE, "QoL")
        reg.mandate(EXTENSION_KICKREASON, "needed")
        ids = [ext_id for ext_id, _, _, _ in reg.enabled_only()]
        self.assertEqual(ids, [EXTENSION_CHATTYPE])
