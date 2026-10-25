import "server-only";
import { timingSafeEqual } from "node:crypto";

export function passwordIsValid(value: unknown) {
  const expected = process.env.KEIBA_ACCESS_PASSWORD;
  if (!expected || typeof value !== "string" || value.length !== expected.length) return false;
  const input = Buffer.from(value); const target = Buffer.from(expected);
  return input.length === target.length && timingSafeEqual(input, target);
}
