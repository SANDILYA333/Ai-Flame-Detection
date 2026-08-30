/**
  ******************************************************************************
  * @file    tim3_chirp_pwm.c
  * @brief   STM32 TIM3 Initialization & 20kHz Chirp Frequency Generation Module
  ******************************************************************************
  */

#include "tim3_chirp_pwm.h"

/* Timer Handle Definition */
TIM_HandleTypeDef htim3;

/**
  * @brief TIM3 Initialization Function
  * @param None
  * @retval None
  */
void MX_TIM3_Init(void)
{
  TIM_ClockConfigTypeDef sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};
  TIM_OC_InitTypeDef sConfigOC = {0};

  /*
   * Frequency calculation:
   * PWM_Freq = TIM3_CLK_FREQ_HZ / ((Prescaler + 1) * (Period + 1))
   * For 20 kHz at 84 MHz Timer Clock:
   * Period (ARR) = (84,000,000 / 20,000) - 1 = 4199
   */

  htim3.Instance = TIM3;
  htim3.Init.Prescaler = 0;
  htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim3.Init.Period = 4199;                          /* 20 kHz initial period */
  htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;

  if (HAL_TIM_Base_Init(&htim3) != HAL_OK)
  {
    Error_Handler();
  }

  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim3, &sClockSourceConfig) != HAL_OK)
  {
    Error_Handler();
  }

  if (HAL_TIM_PWM_Init(&htim3) != HAL_OK)
  {
    Error_Handler();
  }

  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim3, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }

  /* PWM Channel 1 Configuration */
  sConfigOC.OCMode = TIM_OCMODE_PWM1;
  sConfigOC.Pulse = 2100;                            /* 50% Duty Cycle (ARR / 2) */
  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;

  if (HAL_TIM_PWM_ConfigChannel(&htim3, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
  {
    Error_Handler();
  }

  /* GPIO Pin Muxing Configuration */
  HAL_TIM_MspPostInit(&htim3);
}

/**
  * @brief TIM3 MSP Initialization (Clocks and GPIO)
  * @param htim_base: TIM base handle
  * @retval None
  */
void HAL_TIM_Base_MspInit(TIM_HandleTypeDef* htim_base)
{
  if (htim_base->Instance == TIM3)
  {
    /* Enable TIM3 Peripheral Clock */
    __HAL_RCC_TIM3_CLK_ENABLE();
  }
}

/**
  * @brief TIM3 Post-Init (Configures PWM Output Pin)
  * @param htim: TIM handle
  * @retval None
  */
void HAL_TIM_MspPostInit(TIM_HandleTypeDef* htim)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  if (htim->Instance == TIM3)
  {
    /* Enable GPIOA Clock (for PA6 - TIM3_CH1) */
    __HAL_RCC_GPIOA_CLK_ENABLE();

    /** TIM3 GPIO Configuration
      * PA6 ------> TIM3_CH1
      */
    GPIO_InitStruct.Pin = GPIO_PIN_6;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF2_TIM3;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
  }
}

/**
  * @brief Start PWM Output on Channel 1
  */
void TIM3_Start_PWM(void)
{
  HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
}

/**
  * @brief Stop PWM Output on Channel 1
  */
void TIM3_Stop_PWM(void)
{
  HAL_TIM_PWM_Stop(&htim3, TIM_CHANNEL_1);
}

/**
  * @brief Dynamically set PWM frequency maintaining 50% duty cycle
  * @param freq_hz: Desired frequency in Hz (e.g. 1000 to 20000 Hz)
  */
void TIM3_Set_Frequency(uint32_t freq_hz)
{
  if (freq_hz == 0) return;

  uint32_t arr = (TIM3_CLK_FREQ_HZ / freq_hz) - 1;

  /* Safeguard for 16-bit Timer Limit (ARR <= 65535) */
  if (arr > 65535)
  {
    arr = 65535;
  }

  __HAL_TIM_SET_AUTORELOAD(&htim3, arr);
  __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, arr / 2); /* 50% duty */
}

/**
  * @brief Simple microsecond delay helper using DWT or SysTick
  */
static void Delay_us(uint32_t us)
{
  uint32_t count = us * (SystemCoreClock / 1000000UL) / 4;
  while (count--)
  {
    __NOP();
  }
}

/**
  * @brief Execute linear chirp frequency sweep up to 20 kHz
  * @param start_freq_hz: e.g. 1000 (1 kHz)
  * @param end_freq_hz:   e.g. 20000 (20 kHz)
  * @param step_hz:       e.g. 100 Hz step
  * @param step_delay_us: e.g. 500 us per step
  */
void TIM3_Run_Chirp_Sweep(uint32_t start_freq_hz, uint32_t end_freq_hz, uint32_t step_hz, uint32_t step_delay_us)
{
  TIM3_Start_PWM();

  for (uint32_t f = start_freq_hz; f <= end_freq_hz; f += step_hz)
  {
    TIM3_Set_Frequency(f);
    Delay_us(step_delay_us);
  }

  TIM3_Stop_PWM();
}
