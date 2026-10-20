// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract EvidenceAnchor {
    address public owner;
    uint256 public batchCount;

    struct Batch {
        bytes32 root;
        uint32 leafCount;
        uint64 anchoredAt;
    }

    mapping(uint256 => Batch) private batches;

    event RootAnchored(
        uint256 indexed batchId,
        bytes32 root,
        uint32 leafCount,
        uint64 anchoredAt
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function anchorRoot(bytes32 root, uint32 leafCount)
        external
        onlyOwner
        returns (uint256 batchId)
    {
        require(root != bytes32(0), "empty root");
        require(leafCount > 0, "no leaves");

        batchId = ++batchCount;
        batches[batchId] = Batch(root, leafCount, uint64(block.timestamp));

        emit RootAnchored(
            batchId,
            root,
            leafCount,
            uint64(block.timestamp)
        );
    }

    function getBatch(uint256 id)
        external
        view
        returns (bytes32 root, uint32 leafCount, uint64 anchoredAt)
    {
        Batch memory batch = batches[id];
        require(batch.root != bytes32(0), "unknown batch");
        return (batch.root, batch.leafCount, batch.anchoredAt);
    }
}