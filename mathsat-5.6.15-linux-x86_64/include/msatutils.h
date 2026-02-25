#ifndef MSAT_MSATUTILS_H_INCLUDED
#define MSAT_MSATUTILS_H_INCLUDED

#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif

enum {
    MSAT_SUBPROCESS_PIPE_STDIN = 1,
    MSAT_SUBPROCESS_PIPE_STDOUT = 2,
    MSAT_SUBPROCESS_PIPE_STDERR = 4
};

typedef struct {
    unsigned int pipe_flags;
    char *const *envp;
} msat_subprocess_opts;

FILE *msat_open_fd(int fd, const char *mode);
int msat_get_fd(FILE *f);
void msat_close_fd(int fd);

typedef int (*msat_subprocess_communicate_func)(int child_stdin,
                                                int child_stdout,
                                                int child_stderr,
                                                void *user_data);

int msat_subprocess_popen(const char *path, char *const args[],
                          msat_subprocess_communicate_func func, void *data,
                          msat_subprocess_opts opts);

#ifdef __cplusplus
} /* extern "C" */
#endif


#endif /* MSAT_MSATUTILS_H_INCLUDED */
