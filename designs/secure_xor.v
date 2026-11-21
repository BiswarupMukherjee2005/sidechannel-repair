// Secure 2-share masked XOR: computes sharewise without recombining secrets.
module secure_xor(
    input  clk,
    input  a0, a1,   // shares of secret a
    input  b0, b1,   // shares of secret b
    input  r,        // unused in linear XOR, kept for uniform interface
    output reg y0, y1
);
    always @(posedge clk) begin
        y0 <= a0 ^ b0;
        y1 <= a1 ^ b1;
    end
endmodule
