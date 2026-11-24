// Box.asm - Nand2Tetris capstone, Samarth Sharma, Roll No. 2501730279, K = 79
// While any key is pressed: draw a black box. When released: clear it.
// Box: starts at row K = 79, 20 rows tall, 16 * ((79 mod 4) + 1) = 64 px = 4 words wide.
// First word address = SCREEN + 32*79 = 16384 + 2528 = 18912.
// R12 = colour (-1 black / 0 white), R13 = screen pointer,
// R14 = row counter, R15 = word counter.

(LOOP)
    @KBD
    D=M
    @SET_BLACK
    D;JNE           // key pressed -> black

(SET_WHITE)
    @R12
    M=0             // no key -> white
    @FILL_SETUP
    0;JMP

(SET_BLACK)
    @R12
    M=-1

(FILL_SETUP)
    @18912          // SCREEN + 32*79
    D=A
    @R13
    M=D
    @20             // 20 rows
    D=A
    @R14
    M=D

(ROW)
    @4              // 4 words per row (64 px)
    D=A
    @R15
    M=D

(WORD)
    @R12
    D=M
    @R13
    A=M
    M=D             // RAM[R13] = colour
    @R13
    M=M+1           // next word
    @R15
    MD=M-1
    @WORD
    D;JGT           // more words in this row?

    @28             // skip the other 32 - 4 = 28 words of the row
    D=A
    @R13
    M=D+M
    @R14
    MD=M-1
    @ROW
    D;JGT           // more rows?

    @LOOP
    0;JMP
