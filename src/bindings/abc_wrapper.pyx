# distutils: language = c++

from libc.stdlib cimport malloc, free
from libc.string cimport strcpy, strlen
from cpython.version cimport PY_MAJOR_VERSION
from src.utils.suppress import suppress_stdout_stderr

cdef extern from "base/main/main.h":
    ctypedef struct Abc_Frame_t:
        pass
    ctypedef struct Abc_Ntk_t:
        pass

    void Abc_Start()
    void Abc_Stop()
    Abc_Frame_t * Abc_FrameGetGlobalFrame()
    int Abc_FrameReadProbStatus(Abc_Frame_t * pAbc)
    void * Abc_FrameReadCex(Abc_Frame_t * pAbc)
    Abc_Ntk_t * Abc_FrameReadNtk(Abc_Frame_t * p)

cdef extern from "base/cmd/cmd.h":
    int Cmd_CommandExecute(Abc_Frame_t * pAbc, const char * sCommand)

cdef extern from "base/abc/abc.h":
    ctypedef struct Abc_Cex_t:
        int iPo
        int nRegs
        int nBits
        unsigned * pData
    
    ctypedef struct Abc_Obj_t:
        pass

    # Utility to check bit in CEX
    int Abc_InfoHasBit(unsigned * p, int i)
    
    # Network accessors
    int Abc_NtkPiNum(Abc_Ntk_t * pNtk)
    Abc_Obj_t * Abc_NtkPi(Abc_Ntk_t * pNtk, int i)
    char * Abc_ObjName(Abc_Obj_t * pNode)

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
            Dict[str, int] representing the Counter Example (input assignment) if SAT.
            Error if Undecided.
        """
        cdef int status
        cdef Abc_Cex_t * pCex = NULL
        cdef Abc_Ntk_t * pNtk = NULL
        cdef Abc_Obj_t * pPi
        cdef char * pName
        cdef int i
        cdef int nPis

        # Suppress ABC Output
        with suppress_stdout_stderr():
            # 1. Read
            # strict verilog reader in ABC
            self.run_command(f"read_verilog {verilog_file}")
            
            # 2. Convert to AIG (blast) for solving
            # strash is standard
            self.run_command("strash")
            
            # 3. Solve
            self.run_command("iprove")
            
            # 4. Check status
            # 1=UNSAT (Property holds), 0=SAT (Property fails), -1=UNDEC
            status = Abc_FrameReadProbStatus(self._frame)
            
            if status == 0:
                 pCex = <Abc_Cex_t *>Abc_FrameReadCex(self._frame)
                 pNtk = Abc_FrameReadNtk(self._frame)
        
        if status == 1:
            return None # Verified!
            
        if status == 0:
            # Failed, get CEX
            if pCex == NULL:
                # Try to get CEX again if it wasn't captured? 
                pCex = <Abc_Cex_t *>Abc_FrameReadCex(self._frame)
                if pCex == NULL:
                     return {} # Should not happen if SAT
            
            if pNtk == NULL:
                pNtk = Abc_FrameReadNtk(self._frame)

            # Convert CEX to dict of bits
            cex_map = {}
            
            # Check number of PIs
            nPis = Abc_NtkPiNum(pNtk)
            
            # Iterate over PIs and map to CEX bits
            # CEX usually stores PI bits in order for the frame.
            # Assuming combinational (nFrames=1, nRegs=0).
            
            for i in range(nPis):
                pPi = Abc_NtkPi(pNtk, i)
                pName = Abc_ObjName(pPi)
                name_str = pName.decode('utf-8')
                
                # Check if bit is set in CEX
                if Abc_InfoHasBit(pCex.pData, pCex.nRegs + i):
                    cex_map[name_str] = 1
                else:
                    cex_map[name_str] = 0
                    
            return cex_map
            
        # Undecided
        raise RuntimeError("ABC could not decide the problem (returned -1).")
