import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { network } from "hardhat";

describe("EvidenceAnchor", async function () {
  const { viem } = await network.create();
  const [owner, nonOwner] = await viem.getWalletClients();

  const root = `0x${"ab".repeat(32)}` as `0x${string}`;
  const emptyRoot = `0x${"00".repeat(32)}` as `0x${string}`;

  it("lets the owner anchor a root and records the batch", async function () {
    const anchor = await viem.deployContract("EvidenceAnchor");

    await anchor.write.anchorRoot([root, 3]);

    assert.equal(await anchor.read.batchCount(), 1n);

    const [storedRoot, leafCount, anchoredAt] =
      await anchor.read.getBatch([1n]);

    assert.equal(storedRoot, root);
    assert.equal(leafCount, 3);
    assert.ok(anchoredAt > 0n);
  });

  it("emits RootAnchored with the stored values", async function () {
    const anchor = await viem.deployContract("EvidenceAnchor");

    await viem.assertions.emitWithArgs(
      anchor.write.anchorRoot([root, 3]),
      anchor,
      "RootAnchored",
      [1n, root, 3, (timestamp: bigint) => timestamp > 0n],
    );
  });

  it("rejects a non-owner", async function () {
    const anchor = await viem.deployContract("EvidenceAnchor");

    await viem.assertions.revertWith(
      anchor.write.anchorRoot([root, 1], { account: nonOwner.account }),
      "not owner",
    );
  });

  it("rejects an empty root", async function () {
    const anchor = await viem.deployContract("EvidenceAnchor");

    await viem.assertions.revertWith(
      anchor.write.anchorRoot([emptyRoot, 1]),
      "empty root",
    );
  });

  it("rejects a zero leaf count", async function () {
    const anchor = await viem.deployContract("EvidenceAnchor");

    await viem.assertions.revertWith(
      anchor.write.anchorRoot([root, 0]),
      "no leaves",
    );
  });

  it("rejects an unknown batch", async function () {
    const anchor = await viem.deployContract("EvidenceAnchor");

    await viem.assertions.revertWith(
      anchor.read.getBatch([1n]),
      "unknown batch",
    );
  });
});