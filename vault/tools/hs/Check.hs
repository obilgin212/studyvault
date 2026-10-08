-- Tiny test helper for exercise blocks in Obsidian (Execute Code plugin).
-- Tests block:   import Check
--                main = runTests [ test "double 3" (double 3) 6, ... ]
module Check (Test, test, runTests) where

import Control.Exception (SomeException, evaluate, try)
import Control.Monad (forM)
import Data.List (isPrefixOf)

type Test = IO Bool

-- | test label actual expected
test :: (Show a, Eq a) => String -> a -> a -> Test
test label actual expected = do
  r <- try (evaluate (actual == expected)) :: IO (Either SomeException Bool)
  case r of
    Right True -> putStrLn ("✅ " ++ label ++ " = " ++ show expected) >> pure True
    Right False -> do
      shown <- safeShow actual
      putStrLn ("❌ " ++ label ++ "\n     expected: " ++ show expected ++ "\n     got:      " ++ shown)
      pure False
    Left e -> putStrLn ("💥 " ++ label ++ "\n     crashed:  " ++ firstLine (show e)) >> pure False

safeShow :: Show a => a -> IO String
safeShow x = do
  r <- try (evaluate (length s `seq` s)) :: IO (Either SomeException String)
  pure (either (\e -> "(crashed while printing: " ++ firstLine (show e) ++ ")") id r)
  where s = show x

-- | First useful line of an error, without the temp-file location (line numbers would point into the combined tests+exercise file).
firstLine :: String -> String
firstLine s = case filter (not . ("CallStack" `isPrefixOf`)) (lines s) of
  (l:_) -> tidy l
  [] -> s
  where
    tidy l = case breakOn ".hs:" l of
      Just rest -> let (ln, after) = break (== ':') rest
                   in dropWhile (== ' ') (const (dropLoc after) ln)
      Nothing -> l
    dropLoc (':':r) = let r' = dropWhile (/= ':') r in if null r' then r else drop 1 r'
    dropLoc r = r
    breakOn pat str
      | null str = Nothing
      | pat `isPrefixOf` str = Just (drop (length pat) str)
      | otherwise = breakOn pat (drop 1 str)

runTests :: [Test] -> IO ()
runTests ts = do
  results <- forM ts id
  let n = length (filter id results)
  putStrLn ""
  putStrLn (if n == length results
    then "🎉 All " ++ show n ++ " tests passed. Now explain *why* it works."
    else show n ++ "/" ++ show (length results) ++ " passed. Read the first ❌/💥 and reason about it before changing code.")
