// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract AuthentiqRegistry {
    struct Record {
        string recordType;
        string payloadDigest;
        string entityId;
        address submitter;
        uint256 timestamp;
    }

    address public owner;
    uint256 public totalRecords;
    mapping(address => bool) public writers;
    mapping(string => Record) private latestRecords;
    mapping(string => uint256) public revisionCounts;

    event RecordEvent(
        string recordId,
        string recordType,
        string payloadDigest,
        string entityId,
        address indexed submitter,
        uint256 timestamp,
        uint256 revision
    );

    event WriterChanged(address indexed writer, bool allowed);

    error NotOwner();
    error NotWriter();
    error EmptyPayloadDigest();

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlyWriter() {
        if (!writers[msg.sender]) revert NotWriter();
        _;
    }

    constructor() {
        owner = msg.sender;
        writers[msg.sender] = true;
        emit WriterChanged(msg.sender, true);
    }

    function setWriter(address writer, bool allowed) external onlyOwner {
        writers[writer] = allowed;
        emit WriterChanged(writer, allowed);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        owner = newOwner;
    }

    function recordEvent(
        string calldata recordId,
        string calldata recordType,
        string calldata payloadDigest,
        string calldata entityId
    ) external onlyWriter {
        if (bytes(payloadDigest).length == 0) revert EmptyPayloadDigest();
        uint256 revision = revisionCounts[recordId] + 1;
        revisionCounts[recordId] = revision;
        totalRecords += 1;
        latestRecords[recordId] = Record({
            recordType: recordType,
            payloadDigest: payloadDigest,
            entityId: entityId,
            submitter: msg.sender,
            timestamp: block.timestamp
        });
        emit RecordEvent(
            recordId,
            recordType,
            payloadDigest,
            entityId,
            msg.sender,
            block.timestamp,
            revision
        );
    }

    function getRecord(string calldata recordId) external view returns (Record memory) {
        return latestRecords[recordId];
    }
}
