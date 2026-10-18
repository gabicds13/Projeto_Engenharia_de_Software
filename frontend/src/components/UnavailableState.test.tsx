import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { UnavailableState } from "./UnavailableState";

describe("UnavailableState", () => {
  it("mostra a mensagem de indisponibilidade da área", () => {
    render(<UnavailableState label="Notificações" />);
    expect(
      screen.getByText(/Notificações indisponível no momento/),
    ).toBeInTheDocument();
  });
});
