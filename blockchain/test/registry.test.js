const { expect } = require("chai");
const { ethers } = require("hardhat");
const { anyValue } = require("@nomicfoundation/hardhat-chai-matchers/withArgs");

describe("AuthentiqRegistry", function () {
  async function deployFixture() {
    const [owner, writer, outsider] = await ethers.getSigners();
    const factory = await ethers.getContractFactory("AuthentiqRegistry");
    const registry = await factory.deploy();
    await registry.waitForDeployment();
    return { registry, owner, writer, outsider };
  }

  it("authorizes the deployer as the first writer", async function () {
    const { registry, owner } = await deployFixture();
    expect(await registry.owner()).to.equal(owner.address);
    expect(await registry.writers(owner.address)).to.equal(true);
  });

  it("records an event with the backend-compatible signature", async function () {
    const { registry } = await deployFixture();
    const digest = "a".repeat(64);

    const [owner] = await ethers.getSigners();
    await expect(registry.recordEvent("reg_001", "registration.created", digest, "reg_001"))
      .to.emit(registry, "RecordEvent")
      .withArgs("reg_001", "registration.created", digest, "reg_001", owner.address, anyValue, 1);

    const stored = await registry.getRecord("reg_001");
    expect(stored.recordType).to.equal("registration.created");
    expect(stored.payloadDigest).to.equal(digest);
    expect(stored.entityId).to.equal("reg_001");
    expect(await registry.totalRecords()).to.equal(1);
  });

  it("increments revisions for repeated record identifiers", async function () {
    const { registry } = await deployFixture();
    await registry.recordEvent("reg_001", "registration.created", "a".repeat(64), "reg_001");
    await registry.recordEvent("reg_001", "version.created", "b".repeat(64), "reg_001");
    expect(await registry.revisionCounts("reg_001")).to.equal(2);
    const stored = await registry.getRecord("reg_001");
    expect(stored.recordType).to.equal("version.created");
    expect(await registry.totalRecords()).to.equal(2);
  });

  it("rejects empty payload digests", async function () {
    const { registry } = await deployFixture();
    await expect(registry.recordEvent("reg_001", "registration.created", "", "reg_001"))
      .to.be.revertedWithCustomError(registry, "EmptyPayloadDigest");
  });

  it("only allows the owner to add writers", async function () {
    const { registry, writer, outsider } = await deployFixture();
    await expect(registry.connect(outsider).setWriter(writer.address, true))
      .to.be.revertedWithCustomError(registry, "NotOwner");
    await registry.setWriter(writer.address, true);
    expect(await registry.writers(writer.address)).to.equal(true);
  });

  it("only allows writers to record events", async function () {
    const { registry, writer, outsider } = await deployFixture();
    await expect(registry.connect(outsider).recordEvent("reg_001", "registration.created", "a".repeat(64), "reg_001"))
      .to.be.revertedWithCustomError(registry, "NotWriter");
    await registry.setWriter(writer.address, true);
    await expect(registry.connect(writer).recordEvent("reg_001", "registration.created", "a".repeat(64), "reg_001"))
      .to.emit(registry, "RecordEvent");
  });
});
