import "@testing-library/jest-dom";

// Mock HTMLCanvasElement.prototype.getContext for jsdom testing
if (typeof window !== "undefined") {
  HTMLCanvasElement.prototype.getContext = () => null;
}

// Global test environment variables (all test fixtures read strictly from env)
process.env.TEST_USER_ID = process.env.TEST_USER_ID || "0f803a08-3091-4e52-bda5-8a54bd57ea2e";
process.env.TEST_USER_EMAIL = process.env.TEST_USER_EMAIL || "aravind@feuji.com";
process.env.TEST_ORG_ID = process.env.TEST_ORG_ID || "c3d0ecce-c25c-48f9-80e2-110ec2f10bd1";
process.env.TEST_CLERK_ORG_ID = process.env.TEST_CLERK_ORG_ID || "org_dev_feuji_001";
process.env.TEST_ORG_NAME = process.env.TEST_ORG_NAME || "Feuji Inc.";
process.env.TEST_ORG_SLUG = process.env.TEST_ORG_SLUG || "feuji-inc";

