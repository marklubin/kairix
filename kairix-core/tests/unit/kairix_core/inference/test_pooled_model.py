"""
Test scenarios for pooled_model module:

1. Test PooledModel initialization:
   - Test with single model instance
   - Test with multiple model instances
   - Test queue initialization
   - Test model validation

2. Test borrow method:
   - Test successful model checkout
   - Test waiting when pool empty
   - Test FIFO queue behavior
   - Test concurrent borrow requests
   - Test timeout handling

3. Test return_model method:
   - Test model returned to pool
   - Test queue size increases
   - Test returned model reusable
   - Test multiple returns

4. Test context manager usage:
   - Test async with statement
   - Test automatic model return
   - Test exception handling
   - Test cleanup on error

5. Test pool exhaustion:
   - Test all models checked out
   - Test waiting queue
   - Test fairness (FIFO)
   - Test starvation prevention

6. Test thread safety:
   - Test concurrent borrows
   - Test concurrent returns
   - Test race conditions
   - Test deadlock prevention

7. Test model lifecycle:
   - Test model state preservation
   - Test model not shared simultaneously
   - Test model cleanup
   - Test resource management

8. Test error scenarios:
   - Test returning wrong model
   - Test double return
   - Test borrow timeout
   - Test model failure handling

9. Test performance:
   - Test checkout latency
   - Test high concurrency
   - Test pool sizing impact
   - Test memory usage

10. Test monitoring:
    - Test pool statistics
    - Test usage metrics
    - Test wait time tracking
    - Test pool health
"""