(defn not_ (p) (cond (p False) (True True) ) )

(defn ff (x) (cond ((atom 'x) 'x) (True (ff (car 'x)))))

(defn subst (x y z)
    (cond
        ((atom 'z) (cond ((eq 'z 'y) 'x) (True 'z)))
        (True (cons
                (subst 'x 'y (car 'z) )
                (subst 'x 'y (cdr 'z) )
              )
        )
    )
)
