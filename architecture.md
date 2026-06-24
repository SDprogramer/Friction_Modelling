flowchart TD
    %% Styling Definitions
    classDef config fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#000;
    classDef pipeline fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000;
    classDef model fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#000;
    classDef eval fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000;

    A([Start Execution]) ::: config
    B[Initialize Parameters & Paths<br/>Gear Ratio N=100] ::: config
    C{Iterate Over Joints<br/>1, 2, 3, 5} ::: pipeline

    A --> B --> C

    subgraph Data_Pipeline [Stage 1: Data Ingestion & Preprocessing]
        D[Read CSV File] ::: pipeline
        E[Parse Timestamps to Datetime] ::: pipeline
        F[Convert Units: Degrees to Radians] ::: pipeline
        G["Calculate Friction Torque (Tf)"] ::: pipeline
    end

    C --> D --> E --> F --> G

    subgraph Model_Pipeline [Stage 2: Modeling & Parameter Estimation]
        H[Sequential Temporal Split<br/>Train 60% | Val 20% | Test 20%] ::: model
        I["Apply Continuous Friction Model"] ::: model
        J[Non-Linear Least Squares Optimization<br/>scipy.optimize.curve_fit] ::: model
        K[Extract Parameters: Tc, Bv, Vs] ::: model
    end

    G --> H --> I --> J --> K

    subgraph Eval_Pipeline [Stage 3: Evaluation & Visualization]
        L[Predict Torque on Test Set] ::: eval
        M[Calculate Performance Metrics<br/>RMSE, MAE, R²] ::: eval
        N[Time-Series Plot: Actual vs Predicted] ::: eval
        O[Residual Plot vs Time] ::: eval
        P[Scatter Plot: Alignment Analysis] ::: eval
        Q[Friction Curve: Torque vs Velocity] ::: eval
    end

    K --> L --> M --> N --> O --> P --> Q
    
    Q --> R{More Joints?} ::: pipeline
    R -- Yes --> C
    R -- No --> S([End Execution]) ::: config
