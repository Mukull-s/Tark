import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { NewInvestigationModal } from "../components/NewInvestigationModal";
import type { CaseMetadata } from "../api/types";

const mockCases: CaseMetadata[] = [
	{
		case_id: "HHG-001",
		opened_at: "2016-11-12 00:00:00",
		trigger_type: "risk_score",
		trigger_text: "High risk score 0.88",
		flagged_txn_id: "3000001",
		card_id: "C10001-A1",
		customer_id: "U10001",
		risk_score: 0.88,
		status: "OPEN",
	},
];

describe("P1.2 — Arbitrary Transaction Investigation Modal", () => {
	it("renders modal and defaults to Alert Queue tab", () => {
		render(
			<NewInvestigationModal
				isOpen={true}
				onClose={vi.fn()}
				onStartInvestigation={vi.fn()}
				cases={mockCases}
			/>,
		);

		expect(screen.getByText("Launch New Investigation")).toBeInTheDocument();
		expect(screen.getByText("Alert Queue Cases (1)")).toBeInTheDocument();
		expect(screen.getByText("Arbitrary Transaction ID")).toBeInTheDocument();
		expect(screen.getByText(/HHG-001/)).toBeInTheDocument();
	});

	it("switches to Arbitrary Transaction tab and allows entering txn id", async () => {
		const handleStartArbitrary = vi.fn();
		const handleClose = vi.fn();

		render(
			<NewInvestigationModal
				isOpen={true}
				onClose={handleClose}
				onStartInvestigation={vi.fn()}
				onStartTransactionInvestigation={handleStartArbitrary}
				cases={mockCases}
			/>,
		);

		// Click the Arbitrary Transaction tab
		await act(async () => {
			fireEvent.click(screen.getByText("Arbitrary Transaction ID"));
		});

		// Should show input and sample IDs
		const input = screen.getByPlaceholderText(/e\.g\. 3047878/);
		expect(input).toBeInTheDocument();

		// Click sample ID 3047878
		const sampleBtn = screen.getByRole("button", { name: "3047878" });
		await act(async () => {
			fireEvent.click(sampleBtn);
		});
		expect((input as HTMLInputElement).value).toBe("3047878");

		// Click Investigate Transaction
		const submitBtn = screen.getByRole("button", { name: "Investigate Transaction" });
		await act(async () => {
			fireEvent.click(submitBtn);
		});

		expect(handleStartArbitrary).toHaveBeenCalledWith("3047878");
	});

	it("displays validation error when transaction ID is empty", async () => {
		render(
			<NewInvestigationModal
				isOpen={true}
				onClose={vi.fn()}
				onStartInvestigation={vi.fn()}
				onStartTransactionInvestigation={vi.fn()}
				cases={mockCases}
			/>,
		);

		await act(async () => {
			fireEvent.click(screen.getByText("Arbitrary Transaction ID"));
		});

		const submitBtn = screen.getByRole("button", { name: "Investigate Transaction" });
		await act(async () => {
			fireEvent.click(submitBtn);
		});

		expect(screen.getByText("Please enter a valid Transaction ID.")).toBeInTheDocument();
	});
});

