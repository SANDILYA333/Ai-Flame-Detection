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

/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Exported constants --------------------------------------------------------*/
#define TIM3_CLK_FREQ_HZ       84000000UL   /* Adjust to your APB1 Timer Clock (e.g., 84MHz / 72MHz / 80MHz) */
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
