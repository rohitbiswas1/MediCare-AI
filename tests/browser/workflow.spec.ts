import { test, expect, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";

async function signUp(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Synthetic Browser Tester");
  await page
    .getByLabel("Email address")
    .fill(`browser-${randomUUID()}@example.com`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Synthetic-browser-password-123");
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page).toHaveURL(/dashboard/);
  await expect(
    page.getByRole("heading", {
      name: "A little clarity. A little peace of mind.",
    }),
  ).toBeVisible();
}
async function cleanup(page: Page) {
  await page.evaluate(async () => {
    const csrf =
      document.cookie
        .split("; ")
        .find((c) => c.startsWith("medicare_csrf="))
        ?.split("=")[1] || "";
    const response = await fetch("/api/v1/users/me", {
      method: "DELETE",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({ confirmation: "DELETE MY ACCOUNT" }),
    });
    if (!response.ok) throw new Error("Test account cleanup failed");
  });
}

test("landing, responsive layout, and accessible registration", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Understand.*your health/i }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: `test-results/landing-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await signUp(page);
  try {
    await expect(page.getByText("Your health story starts here")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
    await page.screenshot({
      path: `test-results/dashboard-${testInfo.project.name}.png`,
      fullPage: true,
    });
    await page.getByLabel("Language", { exact: true }).selectOption("hi");
    await expect(
      page.getByRole("heading", { name: "थोड़ी स्पष्टता। थोड़ा सुकून।" }),
    ).toBeVisible();
    await page.getByLabel("भाषा", { exact: true }).selectOption("bn");
    await expect(
      page.getByRole("heading", { name: "একটু স্বচ্ছতা। একটু স্বস্তি।" }),
    ).toBeVisible();
    await page.getByLabel("ভাষা", { exact: true }).selectOption("en");
    await page.getByRole("button", { name: "Toggle dark mode" }).click();
    await expect(page.locator("html")).toHaveClass(/dark/);
    await page.goto("/admin");
    await expect(page.locator("main .notice[role=alert]")).toContainText(
      "Administrator access is required",
    );
  } finally {
    await cleanup(page);
  }
});

test("report upload, queued OCR, evidence display, and deletion", async ({
  page,
}) => {
  await signUp(page);
  try {
    await page.goto("/upload");
    await page.getByLabel("Report type").selectOption("heart_rate");
    // Actual PNG rendered locally; no network fixture or patient data.
    const data = await page.evaluate(() => {
      const canvas = document.createElement("canvas");
      canvas.width = 1400;
      canvas.height = 650;
      const c = canvas.getContext("2d")!;
      c.fillStyle = "white";
      c.fillRect(0, 0, 1400, 650);
      c.fillStyle = "black";
      c.font = "42px sans-serif";
      c.fillText("SYNTHETIC TEST - NOT A PATIENT", 50, 80);
      c.fillText("Heart rate: 88 bpm", 50, 180);
      return canvas.toDataURL("image/png").split(",")[1];
    });
    await page.getByLabel("Choose a document").setInputFiles({
      name: "synthetic-browser.png",
      mimeType: "image/png",
      buffer: Buffer.from(data, "base64"),
    });
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: "Upload & explain" }).click();
    await expect(page).toHaveURL(/reports\/[a-f0-9-]+/);
    await expect(
      page.getByRole("heading", { name: "Your report, explained" }),
    ).toBeVisible({ timeout: 45000 });
    await expect(page.getByText("88", { exact: false }).first()).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Original extracted text" }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Delete report", exact: true })
      .click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Delete report", exact: true })
      .click();
    await expect(page).toHaveURL(/\/reports$/);
    await expect(page.getByText("Your health story starts here")).toBeVisible();
  } finally {
    await cleanup(page);
  }
});

test("prescription confirmation and privacy controls persist", async ({
  page,
}) => {
  await signUp(page);
  let erased = false;
  try {
    await page.goto("/prescriptions");
    const data = await page.evaluate(() => {
      const c = document.createElement("canvas");
      c.width = 1400;
      c.height = 650;
      const ctx = c.getContext("2d")!;
      ctx.fillStyle = "white";
      ctx.fillRect(0, 0, c.width, c.height);
      ctx.fillStyle = "black";
      ctx.font = "40px sans-serif";
      ctx.fillText("SYNTHETIC PRESCRIPTION TEST ONLY", 40, 80);
      ctx.fillText(
        "Confirm all unclear handwriting with a pharmacist.",
        40,
        160,
      );
      return c.toDataURL("image/png").split(",")[1];
    });
    await page.getByLabel("Choose a document").setInputFiles({
      name: "synthetic-prescription.png",
      mimeType: "image/png",
      buffer: Buffer.from(data, "base64"),
    });
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: "Upload & explain" }).click();
    await expect(page).toHaveURL(/prescriptions\/[a-f0-9-]+/);
    await page
      .getByLabel("Medicine name", { exact: true })
      .fill("Synthetic medicine for test");
    await page.getByLabel("Strength", { exact: true }).fill("as written");
    await page.getByLabel("Dosage form", { exact: true }).fill("as written");
    await page.getByRole("checkbox").check();
    await page
      .getByRole("button", { name: "Save confirmed prescription" })
      .click();
    await expect(
      page.getByRole("heading", {
        name: "Continue with your confirmed details",
      }),
    ).toBeVisible();
    await page.reload();
    await expect(page.getByLabel("Medicine name", { exact: true })).toHaveValue(
      "Synthetic medicine for test",
    );
    await page.goto("/privacy");
    const toggle = page.getByRole("checkbox", {
      name: "Optional third-party AI processing",
    });
    await toggle.check();
    await expect(page.getByRole("status")).toContainText("Saved");
    await page.reload();
    await expect(toggle).toBeChecked();
    await toggle.uncheck();
    await expect(page.getByRole("status")).toContainText("Saved");
    await page.getByRole("button", { name: "Delete my account" }).click();
    await page
      .getByRole("textbox", { name: "Type DELETE MY ACCOUNT to confirm" })
      .fill("DELETE MY ACCOUNT");
    await page.getByRole("button", { name: "Delete my account" }).click();
    await expect(page).toHaveURL("/");
    erased = true;
  } finally {
    if (!erased) await cleanup(page);
  }
});
