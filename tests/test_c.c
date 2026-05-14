/*
 * test_c.c
 * A simple C program with several distinct functions so .eh_frame
 * has plenty of FDEs to find.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---------- helper functions ---------- */

static int add(int a, int b) {
    return a + b;
}

static int multiply(int a, int b) {
    int result = 0;
    for (int i = 0; i < b; i++)
        result = add(result, a);
    return result;
}

static void reverse_string(char *s) {
    int lo = 0, hi = (int)strlen(s) - 1;
    while (lo < hi) {
        char tmp = s[lo];
        s[lo++]  = s[hi];
        s[hi--]  = tmp;
    }
}

static long fibonacci(int n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

static void print_array(int *arr, int len) {
    for (int i = 0; i < len; i++)
        printf("%d%s", arr[i], i < len - 1 ? ", " : "\n");
}

static void bubble_sort(int *arr, int len) {
    for (int i = 0; i < len - 1; i++)
        for (int j = 0; j < len - i - 1; j++)
            if (arr[j] > arr[j + 1]) {
                int tmp  = arr[j];
                arr[j]   = arr[j + 1];
                arr[j + 1] = tmp;
            }
}

/* ---------- main ---------- */

int main(void) {
    /* arithmetic */
    printf("add(3,4)      = %d\n", add(3, 4));
    printf("multiply(6,7) = %d\n", multiply(6, 7));

    /* string */
    char buf[] = "hello";
    reverse_string(buf);
    printf("reverse       = %s\n", buf);

    /* recursion */
    printf("fib(10)       = %ld\n", fibonacci(10));

    /* sorting */
    int arr[] = {5, 3, 8, 1, 9, 2, 7, 4, 6};
    int len   = sizeof(arr) / sizeof(arr[0]);
    bubble_sort(arr, len);
    printf("sorted        = ");
    print_array(arr, len);

    return 0;
}
