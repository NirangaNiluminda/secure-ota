import { expect } from "chai";
import * as fs from "fs";
import * as path from "path";

/**
 * The frozen ABI in packages/shared is what the device client, the dashboard and
 * the attack harness are all written against. A seam is only frozen if something
 * checks; this test is that something.
 *
 * It compares the compiled contract's ABI against the shared spec entry by
 * entry, so renaming a parameter type, changing a mutability or dropping a
 * custom error fails the contract build rather than surfacing as a confusing
 * decode error in somebody else's package two days before the deadline.
 */

const SPEC_PATH = path.join(
  __dirname,
  "..",
  "..",
  "shared",
  "abi",
  "FirmwareRegistry.json"
);

const ARTIFACT_PATH = path.join(
  __dirname,
  "..",
  "artifacts",
  "contracts",
  "FirmwareRegistry.sol",
  "FirmwareRegistry.json"
);

type AbiParam = { type: string; components?: AbiParam[]; indexed?: boolean };
type AbiEntry = {
  type: string;
  name?: string;
  inputs?: AbiParam[];
  outputs?: AbiParam[];
  stateMutability?: string;
};

/** Expand tuples so `(uint256,bytes32,string,uint256,bool)` compares by value. */
function canonicalType(param: AbiParam): string {
  if (param.type.startsWith("tuple")) {
    const inner = (param.components ?? []).map(canonicalType).join(",");
    return `(${inner})${param.type.slice("tuple".length)}`;
  }
  return param.type;
}

function signatureOf(entry: AbiEntry): string {
  const params = (entry.inputs ?? []).map(canonicalType).join(",");
  return `${entry.name}(${params})`;
}

function outputsOf(entry: AbiEntry): string {
  return (entry.outputs ?? []).map(canonicalType).join(",");
}

const spec = JSON.parse(fs.readFileSync(SPEC_PATH, "utf8"));
const frozenAbi: AbiEntry[] = spec.abi;

describe("ABI conformance with the frozen shared spec", () => {
  let compiled: AbiEntry[];

  before(() => {
    expect(
      fs.existsSync(ARTIFACT_PATH),
      "run `npm run compile` before the conformance test"
    ).to.equal(true);
    compiled = JSON.parse(fs.readFileSync(ARTIFACT_PATH, "utf8")).abi;
  });

  it("declares a spec version so a deliberate change is visible", () => {
    expect(spec.specVersion).to.match(/^\d+\.\d+\.\d+$/);
  });

  for (const entry of frozenAbi.filter((e) => e.type === "function")) {
    it(`implements function ${signatureOf(entry)}`, () => {
      const match = compiled.find(
        (candidate) =>
          candidate.type === "function" &&
          signatureOf(candidate) === signatureOf(entry)
      );

      expect(match, `missing from the contract: ${signatureOf(entry)}`).to.not.be
        .undefined;
      expect(outputsOf(match!), "return types differ").to.equal(
        outputsOf(entry)
      );
      expect(match!.stateMutability, "mutability differs").to.equal(
        entry.stateMutability
      );
    });
  }

  for (const entry of frozenAbi.filter((e) => e.type === "event")) {
    it(`emits event ${signatureOf(entry)}`, () => {
      const match = compiled.find(
        (candidate) =>
          candidate.type === "event" &&
          signatureOf(candidate) === signatureOf(entry)
      );

      expect(match, `missing from the contract: ${signatureOf(entry)}`).to.not.be
        .undefined;

      // Indexing is part of the wire format: it decides which fields land in
      // topics and which in data, so the dashboard's filters depend on it.
      const frozenIndexed = (entry.inputs ?? []).map((i) => Boolean(i.indexed));
      const actualIndexed = (match!.inputs ?? []).map((i) => Boolean(i.indexed));
      expect(actualIndexed, "indexed flags differ").to.deep.equal(frozenIndexed);
    });
  }

  for (const entry of frozenAbi.filter((e) => e.type === "error")) {
    it(`defines error ${signatureOf(entry)}`, () => {
      const match = compiled.find(
        (candidate) =>
          candidate.type === "error" &&
          signatureOf(candidate) === signatureOf(entry)
      );
      expect(match, `missing from the contract: ${signatureOf(entry)}`).to.not.be
        .undefined;
    });
  }

  it("keeps every documented invariant stated in the spec", () => {
    // Prose, not executable — but it must not silently disappear, because the
    // invariants are the reason the signatures mean anything.
    expect(spec.invariants).to.be.an("array");
    expect(spec.invariants.length).to.be.greaterThan(0);
  });
});
