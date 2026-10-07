# Component 02 Colab training

Run `train_wav2vec2_colab.ipynb` and `train_ast_colab.ipynb` separately. Both use the same package label mapping and existing splits: 29,402 training examples, 925 clean validation clips and 924 clean test clips. No new dataset partition or audio augmentation is created.

1. Upload the existing `colab_training_package.zip` to your Google Drive. Open one notebook in Colab and select a GPU runtime.
2. Run the dependency cell in a fresh runtime. If Colab requests a restart, restart before imports. Retain Colab's matching PyTorch/torchaudio installation; PyTorch >=2.6 is required. Edit `ZIP_ON_DRIVE` and `DRIVE_ROOT` in settings.
3. Run settings, extraction and integrity checks. CSV paths resolve relative to the extracted package root. Checks cover counts, labels, audio headers, hashes and disjoint parent/final-group membership. Quality flags are retained without further filtering.
4. Practical mode uses `N_TRIALS=3`, `FULL_GROUPED_CV=False`. Set `RUN_TUNING=True` before running the tuning cell. This uses one deterministic grouped holdout within training, scoring its clean examples; all siblings in the held-out groups are withheld from fold training. Set `FULL_GROUPED_CV=True` for all three folds and mean/population-standard-deviation macro F1. Three trials are a small search, not an exhaustive evaluation of every combination.
5. Inspect tuning results, then set `RUN_FINAL_TRAINING=True` and run final training. It trains on the supplied training partition and selects the checkpoint by original-validation macro F1. If changing flags after setup, edit their values in a new Colab cell rather than rerunning setup and creating a new run directory.
6. Only after model selection is final, set `RUN_FINAL_TEST=True` in the separate test cell. Do not revise hyperparameters based on test results. The cell refuses to overwrite a previous test evaluation.
7. Optionally enable the upload-inference cell. It reports segment predictions and duration-weighted softmax confidence for longer files. Confidence is uncalibrated and the classifier has no unknown-species rejection.

The checkpoints are `facebook/wav2vec2-base` and `MIT/ast-finetuned-audioset-10-10-0.4593`. Each loads its matching feature extractor and replaces/initializes the classification head for ten labels. Wav2Vec2 freezes its convolutional feature encoder. AST retains its checkpoint's 128 Mel bins, 1,024-frame input and AudioSet normalization; five-second inputs are feature-padded by the extractor. Checkpoint revisions and software versions are recorded. Checkpoint head initialization warnings are expected.

Optuna searches learning rate {1e-5, 2e-5, 3e-5, 5e-5}, dropout {0.1, 0.2, 0.3}, maximum epochs {5, 10, 15}, batch size {4, 8, 16}, and weight decay {0.01, 0.05, 0.1}. Training uses AdamW, cosine scheduling with 10% warmup, mixed precision, four-step gradient accumulation, gradient clipping at 1.0 and early stopping with patience 2. Seed 42 controls Optuna, initialization and loaders; group folds are deterministic. Hardware/library differences may still affect reproducibility.

Class weights are `clip(sqrt(N / (10 * n_class)), 0.5, 2.0)`, calculated only from the rows used for that fit. The square root and bounds limit excessive weights. Weighted cross-entropy is normalized by total target-class weight, including across accumulation windows. Validation and test never determine weights.

GPU OOM trials are logged/pruned, not silently altered. If no trial fits, start a new run with `BATCH_CHOICES=[4]` or a larger GPU. Even practical mode can take substantial time on 29,402 examples. AST feature extraction is performed on demand to avoid a large feature cache. Trial checkpoints also consume Drive storage. Final training OOM stops before test evaluation.

Artifacts are saved under `model_runs/wav2vec2/<run_id>/` or `model_runs/ast/<run_id>/`: best model and extractor, class weights/counts, label mapping, seed/environment, hyperparameters, tuning/fold scores, training curves, validation/test metrics, per-species precision/recall, predictions and confusion matrices. Checkpoints support inference; full interrupted optimizer-state resumption is not implemented.

Known provenance, low-energy, padding and audibility limitations remain. Group separation does not prove independent recording events; clean test results do not demonstrate robustness to independently recorded noise. These notebooks were structure/syntax checked, not trained or GPU-runtime tested. No training results are supplied.

API references: [Wav2Vec2](https://huggingface.co/docs/transformers/v4.57.1/model_doc/wav2vec2), [AST](https://huggingface.co/docs/transformers/v4.57.1/model_doc/audio-spectrogram-transformer), [grouped folds](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html).

## Small CPU experiment for the viva

GPU is selected automatically when available, otherwise CPU. Full GPU settings remain unchanged. CPU uses float32 without AMP, gradient scaling or gradient checkpointing; CUDA cache operations are guarded. No training starts by default.

1. Run section 1 (dependencies and runtime).
2. In section 2, set `CPU_SMOKE_TEST=True`, edit your Drive ZIP path, and run the settings cell. Keep `RUN_TUNING=False` and `RUN_FINAL_TRAINING=False` while checking setup.
3. Run sections 3-7. Section 6 selects exactly two clean clips per class for training (20 total) and one per class for validation (10 total), from disjoint training-only recording-group pools. Unsampled siblings are unused. Original manifests are neither changed nor filtered on disk.
4. Set `RUN_TUNING=True` in a new cell, then run section 8. One fixed-configuration Optuna trial uses batch size 1 and maximum one epoch. It actually receives the small subset. This is a smoke test, not meaningful hyperparameter optimization.
5. Read printed training loss, validation accuracy and macro F1. The trial saves its successful best checkpoint, feature extractor and history/curves to `model_runs/<model>/cpu_smoke_test/<run_id>/`. Selection CSVs document the exact clips used.
6. Optionally set `RUN_FINAL_TRAINING=True` in a new cell and run section 9 for the full classification report/plots on the same small holdout. This repeats at most one epoch on the 20 clips, never the full training manifest. Keep section 10 disabled: smoke mode explicitly blocks original test evaluation. Section 11 can use the checkpoint from section 9 for optional upload inference.

Smoke-test results are **preliminary and not comparable to full-model results**. Ten validation clips yield unstable metrics and do not establish research performance. Even one transformer epoch on CPU may take time and substantial RAM. Leave `CPU_SMOKE_TEST=False` to retain the ordinary full-dataset workflow. Change experiment mode only by starting a new settings/run directory, not midway through an experiment.
