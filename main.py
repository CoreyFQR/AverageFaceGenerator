import sys

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from avgface.selftest import main
        sys.exit(main())
    from avgface.ui import main
    sys.exit(main())
