// Sample flawed design: a masked AND gate that recombines shares
// before the output, so the secret value appears on a single wire.
module flawed_and(
    input  clk,
    input  a0, a1,   // shares of secret a
    input  b0, b1,   // shares of secret b
    input  r,        // fresh random bit
    output reg y0, y1
);
    wire a = a0 ^ a1;   // BUG: unmasks a
    wire b = b0 ^ b1;   // BUG: unmasks b
    wire y = a & b;
    always @(posedge clk) begin
        y0 <= y ^ r;
        y1 <= r;
    end
endmodule
