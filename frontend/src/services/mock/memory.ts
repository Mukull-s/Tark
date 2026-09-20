import { CaseMemoryItem } from '../../types/investigation';

export const MOCK_MEMORY_CC0141: CaseMemoryItem = {
  case_id: "CC-0141",
  similarity: "HIGH",
  pattern: "card_testing",
  outcome: "confirmed_fraud",
  exposure_usd: 312.50,
  actions_taken: ["DECLINE_TRANSACTION", "BLOCK_CARD", "FILE_REPORT"],
  analyst_notes: "Syndicate pattern: three rapid online authorizations under $2 followed by larger electronics retail purchase. Originating device is Android 7.0 Samsung Browser on SM-G892A hardware. Suspected stolen credential bundle.",
  opened_at: "2016-08-20 14:12:00",
  closed_at: "2016-08-22 09:30:00"
};

export const MOCK_MEMORY_CC0098: CaseMemoryItem = {
  case_id: "CC-0098",
  similarity: "MEDIUM",
  pattern: "card_not_present_new_device",
  outcome: "confirmed_fraud",
  exposure_usd: 540.00,
  actions_taken: ["BLOCK_CARD", "CREATE_CASE"],
  analyst_notes: "Card testing observed from VPN-masked IP address with mismatched billing zip code.",
  opened_at: "2016-07-15 11:00:00",
  closed_at: "2016-07-16 16:45:00"
};

export function getMockCaseMemory(caseId: string): CaseMemoryItem[] {
  if (caseId === "HHG-017") {
    return [MOCK_MEMORY_CC0141, MOCK_MEMORY_CC0098];
  }
  return [MOCK_MEMORY_CC0098];
}
