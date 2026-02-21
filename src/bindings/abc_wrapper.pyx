# distutils: language = c++

from libc.stdlib cimport malloc, free
from libc.string cimport strcpy, strlen
from cpython.version cimport PY_MAJOR_VERSION
import logging
import time
from src.utils.suppress import suppress_stdout_stderr

cdef extern from "base/main/main.h":
    ctypedef struct Abc_Frame_t:
        pass
    void Abc_Start()
    void Abc_Stop()
    Abc_Frame_t * Abc_FrameGetGlobalFrame()

cdef extern from "base/cmd/cmd.h":
    int Cmd_CommandExecute(Abc_Frame_t * pAbc, const char * sCommand)

cdef extern from "base/abc/abc.h":
    ctypedef struct Abc_Cex_t:
        int iPo
        int nRegs
        int nBits
        unsigned * pData

    int Abc_FrameReadProbStatus(Abc_Frame_t * pAbc)
    Abc_Cex_t * Abc_FrameReadCex(Abc_Frame_t * pAbc)
    
    # Utility to check bit in CEX
    int Abc_InfoHasBit(unsigned * p, int i)

# wrapper class
cdef class AbcInterface:
    cdef Abc_Frame_t * _frame
    
    def __cinit__(self):
        Abc_Start()
        self._frame = Abc_FrameGetGlobalFrame()
        
    def __dealloc__(self):
        Abc_Stop()
        
    def run_command(self, str command):
        """Runs an ABC command. Returns the status code (0 = success)."""
        cmd_bytes = command.encode('utf-8')
        return Cmd_CommandExecute(self._frame, cmd_bytes)
        
    def check_sat(self, str verilog_file):
        """
        Reads a Verilog file and checks satisfiability.
        Returns:
            None if UNSAT (Proven).
            List[int] representing the Counter Example (input assignment) if SAT.
            None if Undecided (or error?).
        """
        logger = logging.getLogger(__name__)
        start_time = time.time()
        
        # Suppress ABC Output
        with suppress_stdout_stderr():
            # 1. Read
            # strict verilog reader in ABC
            self.run_command(f"read_verilog {verilog_file}")
            
            # 2. Convert to AIG (blast) for solving
            # strash is standard
            self.run_command("strash")
            
            # 3. Solve
            # iprove is good for sequential, but for combinational SAT 'cec' or 'sat' is enough.
            # Manthan uses 'iprove' or 'cec'. 'cec' checks equivalence.
            # If we have a single output that should be 0 (UNSAT), we want to prove it is constant 0.
            # "iprove" attempts to prove the miter outcomes are constant 0.
            
            # We assume the error formula output is '1' if there is an error (SAT).
            # Wait, Manthan error formula: E(...) is SAT -> Bug.
            # So we want to check satisfiability of the output.
            # 'iprove' tries to prove UNSAT (property holds).
            # If result is UNSAT (property holds), then E is UNSAT -> No Bug.
            # If result is SAT (property fails), E is SAT -> Bug.
            
            self.run_command("iprove")
            
            # 4. Check status
            # 1=UNSAT (Property holds), 0=SAT (Property fails), -1=UNDEC
            status = Abc_FrameReadProbStatus(self._frame)
            
        cdef Abc_Cex_t * pCex = NULL
        if status == 0:
             pCex = <Abc_Cex_t *>Abc_FrameReadCex(self._frame)

        end_time = time.time()
        duration = end_time - start_time
        
        if status == 1:
            logger.info(f"ABC Check: UNSAT in {duration:.4f}s")
            return None # Verified!
            
        if status == 0:
            logger.info(f"ABC Check: SAT in {duration:.4f}s")
            # Failed, get CEX
            # pCex was retrieved inside suppression block if status==0, but capturing pointer is fine?
            # Actually CEX structure is in memory.
            if pCex == NULL:
                # Try to get CEX again if it wasn't captured? 
                # Abc_FrameReadCex just returns the pointer stored in frame.
                pCex = <Abc_Cex_t *>Abc_FrameReadCex(self._frame)
                if pCex == NULL:
                     return [] # Should not happen if SAT

            # Convert CEX to list of bits
            # pCex->nRegs is latches (should be 0 for comb)
            # pCex->nBits is inputs?
            # Actually CEX structure in ABC is bit-packed.
            # We need to extract bits for PI (Primary Inputs).
            
            # The CEX bits usually cover PIs for each frame.
            # Here it's combinational, so 1 frame.
            
            cex_bits = []
            # We need to know number of PIs to extract correctly or just extract all bits?
            # Abc_InfoHasBit(pCex->pData, i)
            # The total bits seems to be in pCex->nBits.
            
            for i in range(pCex.nBits):
                if Abc_InfoHasBit(pCex.pData, i):
                    cex_bits.append(1)
                else:
                    cex_bits.append(0)
                    
            return cex_bits
            
        # Undecided
        logger.warning(f"ABC Check: UNDECIDED in {duration:.4f}s")
        raise RuntimeError("ABC could not decide the problem (returned -1).")

