// Properly masked 2-share DOM (Domain-Oriented Masking) AND gate.
// intermediate cross-shares are re-masked with random bit 'r' and registered.
// Secure against 1st-order side-channel attacks.
module secure_and(
    input  clk,
    input  a0, a1,   // shares of secret a
    input  b0, b1,   // shares of secret b
    input  r,        // fresh random mask bit
    output y0, y1    // shares of result y
);
    reg t00, t01, t10, t11;

    always @(posedge clk) begin
        t00 <= a0 & b0;
        t01 <= (a0 & b1) ^ r;
        t10 <= (a1 & b0) ^ r;
        t11 <= a1 & b1;
    end

    assign y0 = t00 ^ t01;
    assign y1 = t11 ^ t10;
endmodule
