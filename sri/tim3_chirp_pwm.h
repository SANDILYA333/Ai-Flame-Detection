/**
  ******************************************************************************
  * @file    tim3_chirp_pwm.h
  * @brief   Header for tim3_chirp_pwm.c - TIM3 PWM & 20kHz Chirp Frequency Generator
  ******************************************************************************
  */

#ifndef __TIM3_CHIRP_PWM_H
#define __TIM3_CHIRP_PWM_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/* STM32 HAL Includes with Smart Fallbacks */
#if defined(__has_include)
  #if __has_include("main.h")
    #include "main.h"
  #elif __has_include("stm32f4xx_hal.h")
    #include "stm32f4xx_hal.h"
  #elif __has_include("stm32f1xx_hal.h")
    #include "stm32f1xx_hal.h"
  #elif __has_include("stm32g4xx_hal.h")
    #include "stm32g4xx_hal.h"
  #endif
#endif

/* Fallback definitions for local IDE linters (Clang) when outside STM32 toolchain */
#ifndef HAL_OK
  typedef enum {
    HAL_OK       = 0x00U,
    HAL_ERROR    = 0x01U,
    HAL_BUSY     = 0x02U,
    HAL_TIMEOUT  = 0x03U
  } HAL_StatusTypeDef;

  typedef struct {
    uint32_t Prescaler;
    uint32_t CounterMode;
    uint32_t Period;
    uint32_t ClockDivision;
    uint32_t RepetitionCounter;
    uint32_t AutoReloadPreload;
  } TIM_Base_InitTypeDef;

  typedef struct {
    void*                 Instance;
    TIM_Base_InitTypeDef Init;
    uint32_t              Channel;
  } TIM_HandleTypeDef;

  typedef struct {
    uint32_t ClockSource;
    uint32_t ClockPolarity;
    uint32_t ClockPrescaler;
    uint32_t ClockFilter;
  } TIM_ClockConfigTypeDef;

  typedef struct {
    uint32_t MasterOutputTrigger;
    uint32_t MasterSlaveMode;
  } TIM_MasterConfigTypeDef;

  typedef struct {
    uint32_t OCMode;
    uint32_t Pulse;
    uint32_t OCPolarity;
    uint32_t OCNPolarity;
    uint32_t OCFastMode;
    uint32_t OCIdleState;
    uint32_t OCNIdleState;
  } TIM_OC_InitTypeDef;

  typedef struct {
    uint32_t Pin;
    uint32_t Mode;
    uint32_t Pull;
    uint32_t Speed;
    uint32_t Alternate;
  } GPIO_InitTypeDef;

  #define TIM3 ((void*)0x40000400UL)
  #define GPIOA ((void*)0x40020000UL)
  #define TIM_COUNTERMODE_UP                0x00000000U
  #define TIM_CLOCKDIVISION_DIV1            0x00000000U
  #define TIM_AUTORELOAD_PRELOAD_ENABLE     0x00000080U
  #define TIM_CLOCKSOURCE_INTERNAL          0x00000000U
  #define TIM_TRGO_RESET                    0x00000000U
  #define TIM_MASTERSLAVEMODE_DISABLE       0x00000000U
  #define TIM_OCMODE_PWM1                   0x00000060U
  #define TIM_OCPOLARITY_HIGH               0x00000000U
  #define TIM_OCFAST_DISABLE                0x00000000U
  #define TIM_CHANNEL_1                     0x00000000U
  #define GPIO_PIN_6                        0x0040U
  #define GPIO_MODE_AF_PP                   0x00000002U
  #define GPIO_NOPULL                       0x00000000U
  #define GPIO_SPEED_FREQ_VERY_HIGH         0x00000003U
  #define GPIO_AF2_TIM3                     0x02U

  /* Stub Macros for Linter */
  #define __HAL_RCC_TIM3_CLK_ENABLE()       do { } while(0)
  #define __HAL_RCC_GPIOA_CLK_ENABLE()      do { } while(0)
  #define __HAL_TIM_SET_AUTORELOAD(__H__, __VAL__) do { } while(0)
  #define __HAL_TIM_SET_COMPARE(__H__, __CH__, __VAL__) do { } while(0)
  #define __NOP()                           do { } while(0)

  HAL_StatusTypeDef HAL_TIM_Base_Init(TIM_HandleTypeDef *htim);
  HAL_StatusTypeDef HAL_TIM_ConfigClockSource(TIM_HandleTypeDef *htim, TIM_ClockConfigTypeDef *sClockSourceConfig);
  HAL_StatusTypeDef HAL_TIM_PWM_Init(TIM_HandleTypeDef *htim);
  HAL_StatusTypeDef HAL_TIMEx_MasterConfigSynchronization(TIM_HandleTypeDef *htim, TIM_MasterConfigTypeDef *sMasterConfig);
  HAL_StatusTypeDef HAL_TIM_PWM_ConfigChannel(TIM_HandleTypeDef *htim, TIM_OC_InitTypeDef *sConfig, uint32_t Channel);
  HAL_StatusTypeDef HAL_TIM_PWM_Start(TIM_HandleTypeDef *htim, uint32_t Channel);
  HAL_StatusTypeDef HAL_TIM_PWM_Stop(TIM_HandleTypeDef *htim, uint32_t Channel);
  void HAL_GPIO_Init(void *GPIOx, GPIO_InitTypeDef *GPIO_Init);
  void Error_Handler(void);
  extern uint32_t SystemCoreClock;
#endif

/* Exported constants --------------------------------------------------------*/
#define TIM3_CLK_FREQ_HZ       84000000UL   /* Adjust to your APB1 Timer Clock (e.g. 84MHz / 72MHz / 80MHz) */
#define DEFAULT_CHIRP_MIN_HZ   1000UL       /* 1 kHz */
#define DEFAULT_CHIRP_MAX_HZ   20000UL      /* 20 kHz */

/* Exported types ------------------------------------------------------------*/
extern TIM_HandleTypeDef htim3;

/* Exported functions prototypes ---------------------------------------------*/
void MX_TIM3_Init(void);
void HAL_TIM_MspPostInit(TIM_HandleTypeDef *htim);

void TIM3_Start_PWM(void);
void TIM3_Stop_PWM(void);
void TIM3_Set_Frequency(uint32_t freq_hz);
void TIM3_Run_Chirp_Sweep(uint32_t start_freq_hz, uint32_t end_freq_hz, uint32_t step_hz, uint32_t step_delay_us);

#ifdef __cplusplus
}
#endif

#endif /* __TIM3_CHIRP_PWM_H */
