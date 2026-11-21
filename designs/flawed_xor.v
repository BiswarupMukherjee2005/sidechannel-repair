// Flawed masked XOR: recombines shares of secrets onto internal wires before output.
module flawed_xor(
    input  clk,
    input  a0, a1,   // shares of secret a
    input  b0, b1,   // shares of secret b
    input  r,        // fresh random bit
    output reg y0, y1
);
    wire a = a0 ^ a1;   // BUG: unmasks secret a
    wire b = b0 ^ b1;   // BUG: unmasks secret b
    wire y = a ^ b;

    always @(posedge clk) begin
        y0 <= y ^ r;
        y1 <= r;
    end
endmodule
